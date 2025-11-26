import json
import os
import re
import shutil
import subprocess
import traceback
from pathlib import Path

import litellm
from docker_utils import run_command_in_container
from litellm import completion

# Drop unsupported params for model compatibility
litellm.drop_params = True


def sanitize_traceback(tb_string: str) -> str:
    pattern = r'File "([^"]+)",'

    def replace_path(match):
        full_path = match.group(1)
        # Keep only the filename
        filename = os.path.basename(full_path)
        return f'File "{filename}",'

    sanitized = re.sub(pattern, replace_path, tb_string)

    return sanitized


def is_test_file_or_directory(path: str) -> bool:
    path_lower = path.lower()
    path_parts = Path(path).parts

    if 'tests' in path_parts or '__tests__' in path_parts:
        return True

    filename = Path(path).name.lower()
    test_patterns = [
        'test_',           # Python: test_foo.py
        '_test.',          # Python: foo_test.py
        '.test.',          # JS/TS: foo.test.js
        '.spec.',          # JS/TS: foo.spec.js
        '_spec.',          # Ruby: foo_spec.rb
        'test.',           # Go: foo_test.go (when just 'test.go')
    ]

    for pattern in test_patterns:
        if pattern in filename:
            return True

    return False



class EnhancedTools:
    """Enhanced tools for advanced agent operations"""

    tools_info = [
        {
            "type": "function",
            "function": {
                "name": "codebase_search",
                "description": "Search for code snippets using text-based keyword matching. This tool performs lexical search (exact word matches) using grep/ripgrep, NOT semantic search. Best for finding specific function names, variable names, or exact text patterns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                        "query": {
                            "type": "string",
                            "description": "Keywords to search for in the codebase. Will be split into words and searched as literal text matches. Use specific terms that would appear verbatim in the code.",
                        },
                        "target_directories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Glob patterns for directories to search over",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file. Returns the file contents for the specified line range. Note: Reading files in the /tasks directory or ./run_tests.sh file is restricted.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_file": {
                            "type": "string",
                            "description": "The path of the file to read. You can use either a relative path in the workspace or an absolute path.",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                        "should_read_entire_file": {
                            "type": "boolean",
                            "description": "Whether to read the entire file. Defaults to false.",
                        },
                        "start_line_one_indexed": {
                            "type": "integer",
                            "description": "The one-indexed line number to start reading from (inclusive).",
                        },
                        "end_line_one_indexed_inclusive": {
                            "type": "integer",
                            "description": "The one-indexed line number to end reading at (inclusive).",
                        },
                    },
                    "required": [
                        "target_file",
                        "should_read_entire_file",
                        "start_line_one_indexed",
                        "end_line_one_indexed_inclusive",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_terminal_cmd",
                "description": "Execute a terminal command in the container environment. Commands run in a sandboxed Docker container, not on the user's actual system. IMPORTANT: Web servers, dev servers, and long-running processes (uvicorn, npm run dev, flask run, etc.) MUST use is_background=true to avoid timeouts. Foreground commands have a 120-second timeout.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The terminal command to execute",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this command needs to be run and how it contributes to the goal.",
                        },
                        "is_background": {
                            "type": "boolean",
                            "description": "Whether the command should be run in the background. MUST be true for web servers, dev servers, or any long-running process (e.g., uvicorn, npm run dev, flask run, node server.js, etc.). Set to false only for quick commands that complete immediately.",
                        },
                    },
                    "required": ["command", "is_background"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List the contents of a directory. The quick tool to use for discovery, before using more targeted tools like grep_search or file reading.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relative_workspace_path": {
                            "type": "string",
                            "description": "Path to list contents of, relative to the workspace root.",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                    },
                    "required": ["relative_workspace_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": "This is best for finding exact text matches or regex patterns. Use this tool to run fast, exact regex searches over text files using the ripgrep engine.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The regex pattern to search for",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Whether the search should be case sensitive",
                        },
                        "include_pattern": {
                            "type": "string",
                            "description": "Glob pattern for files to include (e.g. '*.ts' for TypeScript files)",
                        },
                        "exclude_pattern": {
                            "type": "string",
                            "description": "Glob pattern for files to exclude",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Edit a file using structured line-based edits. Supports both creating new files and modifying existing ones.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_file": {
                            "type": "string",
                            "description": "The target file to modify. You can use either a relative path in the workspace or an absolute path.",
                        },
                        "instructions": {
                            "type": "string",
                            "description": "A clear description of what changes are being made to the file.",
                        },
                        "edit_type": {
                            "type": "string",
                            "enum": ["line_edits"],
                            "description": "Type of edit to perform. Only 'line_edits' for structured line-based changes is supported.",
                        },
                        "line_edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["replace", "insert", "delete"],
                                        "description": "Type of line operation",
                                    },
                                    "line_number": {
                                        "type": "integer",
                                        "description": "1-indexed line number where the edit should be applied",
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "New content for replace/insert operations (not needed for delete)",
                                    },
                                },
                                "required": ["type", "line_number"],
                            },
                            "description": "Array of line-based edits to apply (required if edit_type is 'line_edits'). Edits are applied in reverse line order to avoid offset issues.",
                        },
                    },
                    "required": ["target_file", "instructions", "edit_type"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a new file or completely overwrite an existing file. Use this for creating new files or replacing entire file contents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to write, relative to the workspace root.",
                        },
                        "content": {
                            "type": "string",
                            "description": "The complete content to write to the file.",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_replace",
                "description": "Search for exact text in a file and replace it with new text. Performs a simple string replacement - the old_string must match exactly.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to modify, relative to the workspace root.",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "The exact text to find and replace (must match exactly, including whitespace).",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The new text to replace the old text with.",
                        },
                    },
                    "required": ["file_path", "old_string", "new_string"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_search",
                "description": "Fast file search based on fuzzy matching against file path. Use if you know part of the file path but don't know where it's located exactly.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Fuzzy filename to search for",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                    },
                    "required": ["query", "explanation"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_file",
                "description": "Deletes a file at the specified path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_file": {
                            "type": "string",
                            "description": "The path of the file to delete, relative to the workspace root.",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                    },
                    "required": ["target_file"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for real-time information about any topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "The search term to look up on the web. Be specific and include relevant keywords for better results.",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation as to why this tool is being used, and how it contributes to the goal.",
                        },
                    },
                    "required": ["search_term"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_diagram",
                "description": "Creates a Mermaid diagram that will be rendered in the chat UI.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Raw Mermaid diagram definition (e.g., 'graph TD; A-->B;').",
                        }
                    },
                    "required": ["content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_notebook",
                "description": "Use this tool to edit a jupyter notebook cell.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_notebook": {
                            "type": "string",
                            "description": "The path to the notebook file you want to edit.",
                        },
                        "cell_idx": {
                            "type": "number",
                            "description": "The index of the cell to edit (0-based)",
                        },
                        "is_new_cell": {
                            "type": "boolean",
                            "description": "If true, a new cell will be created at the specified cell index. If false, the cell at the specified cell index will be edited.",
                        },
                        "cell_language": {
                            "type": "string",
                            "description": "The language of the cell to edit. Should be STRICTLY one of these: 'python', 'markdown', 'javascript', 'typescript', 'r', 'sql', 'shell', 'raw' or 'other'.",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "The text to replace (must be unique within the cell, and must match the cell contents exactly, including all whitespace and indentation).",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "The edited text to replace the old_string or the content for the new cell.",
                        },
                    },
                    "required": [
                        "target_notebook",
                        "cell_idx",
                        "is_new_cell",
                        "cell_language",
                        "old_string",
                        "new_string",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "api_call",
                "description": "Make HTTP requests to test API endpoints. Useful for testing backend functionality and API integration.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP method to use"
                        },
                        "url": {
                            "type": "string",
                            "description": "The API endpoint URL (can be relative like '/api/users' or absolute)"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers to include in the request"
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body for POST/PUT/PATCH requests"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation of why this API call is being made"
                        }
                    },
                    "required": ["method", "url", "explanation"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "database_query",
                "description": "Execute database queries to test data persistence and retrieval. Useful for verifying backend data operations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["find", "insert", "update", "delete", "aggregate"],
                            "description": "Type of database operation"
                        },
                        "collection": {
                            "type": "string",
                            "description": "MongoDB collection name"
                        },
                        "query": {
                            "type": "object",
                            "description": "Query object (MongoDB syntax)"
                        },
                        "data": {
                            "type": "object",
                            "description": "Data to insert/update (for insert/update operations)"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation of why this database operation is needed"
                        }
                    },
                    "required": ["query_type", "collection", "explanation"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "websocket_test",
                "description": "Test WebSocket/Socket.IO functionality for real-time features like chat, notifications, or live updates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_name": {
                            "type": "string",
                            "description": "Socket.IO event name to test"
                        },
                        "event_data": {
                            "type": "object",
                            "description": "Data to send with the event"
                        },
                        "expected_response": {
                            "type": "string",
                            "description": "Expected response event or behavior"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds (default: 10)"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation of what real-time functionality is being tested"
                        }
                    },
                    "required": ["event_name", "explanation"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ui_test",
                "description": "Test frontend UI functionality by simulating user interactions and checking page state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["screenshot", "click", "type", "navigate", "wait_for_element", "get_text"],
                            "description": "UI action to perform"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for the element (required for click, type, wait_for_element, get_text)"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to type (for type action)"
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to (for navigate action)"
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Timeout in seconds (default: 10)"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "One sentence explanation of what UI functionality is being tested"
                        }
                    },
                    "required": ["action", "explanation"]
                }
            }
        },
    ]

    def __init__(self, container=None, base_path: str = "/", mern_config: dict = None):
        self.container = container
        self.base_path = Path(base_path)
        self.mern_config = mern_config or {
            "api_base_url": "http://localhost:5001",
            "frontend_url": "http://localhost:3000",
            "mongo_uri": "mongodb://localhost:27017/dev-arena",
            "websocket_url": "http://localhost:5001"
        }

    def codebase_search(
        self, query: str, explanation: str = "", target_directories: list = None
    ) -> dict:
        """Text-based codebase search using grep/ripgrep for keyword matching"""
        try:
            results = []
            search_dirs = target_directories if target_directories else ["."]

            # Use ripgrep for better search if available, otherwise fallback to grep
            search_terms = query.lower().split()

            for search_dir in search_dirs:
                if self.container:
                    # First try ripgrep for content search
                    rg_cmd = ["rg", "-i", "--type", "py", "--type", "js", "--type", "ts",
                             "-n", "-C", "2",
                             # Explicit exclusions for safety
                             "-g", "!node_modules/", "-g", "!.venv/", "-g", "!venv/",
                             "-g", "!__pycache__/", "-g", "!.git/", "-g", "!dist/",
                             "-g", "!build/", "-g", "!target/", "-g", "!vendor/",
                             query, str(self.base_path / search_dir)]

                    result = run_command_in_container(self.container, rg_cmd)
                    if result["success"] and result["output"]:
                        # Parse ripgrep output
                        lines = result["output"].split("\n")
                        current_file = None
                        for line in lines:
                            if line and not line.startswith("--"):
                                if ":" in line:
                                    file_path, line_num, content = line.split(":", 2)
                                    if file_path != current_file:
                                        current_file = file_path
                                        results.append({
                                            "file": file_path,
                                            "relevance": 0.9,
                                            "snippet": content.strip(),
                                            "line_number": line_num
                                        })

                    # Fallback to find command for file discovery
                    if not results:
                        cmd = [
                            "find", str(self.base_path / search_dir), "-type", "f",
                            # Exclude common dependency/build directories
                            "-not", "-path", "*/node_modules/*",
                            "-not", "-path", "*/.venv/*",
                            "-not", "-path", "*/venv/*",
                            "-not", "-path", "*/__pycache__/*",
                            "-not", "-path", "*/.git/*",
                            "-not", "-path", "*/dist/*",
                            "-not", "-path", "*/build/*",
                            "-not", "-path", "*/target/*",
                            "-not", "-path", "*/vendor/*",
                            "(", "-name", "*.py", "-o", "-name", "*.js", "-o", "-name", "*.ts",
                            "-o", "-name", "*.jsx", "-o", "-name", "*.tsx", ")",
                            "-exec", "grep", "-l", "-i", query, "{}", ";"
                        ]
                        result = run_command_in_container(self.container, cmd)
                        if result["success"]:
                            files = [f.strip() for f in result["output"].split("\n") if f.strip()]
                            for file in files[:10]:
                                results.append({
                                    "file": file,
                                    "relevance": 0.7,
                                    "snippet": f"Contains '{query}'"
                                })
                else:
                    # Local search with better file content analysis
                    search_path = self.base_path / search_dir

                    # Define exclusion patterns
                    exclude_dirs = {
                        'node_modules', '.venv', 'venv', '__pycache__', '.git',
                        'dist', 'build', 'target', 'vendor', '.next', '.nuxt',
                        '.cache', 'tmp', 'temp', '.gradle', '.m2', 'obj', 'bin'
                    }

                    def should_exclude_path(path: Path) -> bool:
                        """Check if path contains excluded directories"""
                        return any(exc_dir in path.parts for exc_dir in exclude_dirs)

                    for ext in ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java", "*.cpp", "*.c"]:
                        for file in search_path.glob(f"**/{ext}"):
                            if len(results) >= 10:
                                break
                            # Skip excluded directories
                            if should_exclude_path(file):
                                continue
                            try:
                                with open(file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if any(term in content.lower() for term in search_terms):
                                        # Find the best matching line
                                        lines = content.split('\n')
                                        best_line = ""
                                        best_score = 0
                                        for line in lines:
                                            score = sum(1 for term in search_terms if term in line.lower())
                                            if score > best_score:
                                                best_score = score
                                                best_line = line.strip()

                                        results.append({
                                            "file": str(file.relative_to(self.base_path)),
                                            "relevance": min(0.9, 0.6 + best_score * 0.1),
                                            "snippet": best_line or f"Found {best_score} matches in {file.name}"
                                        })
                            except (UnicodeDecodeError, PermissionError):
                                continue

            # Sort by relevance
            results.sort(key=lambda x: x["relevance"], reverse=True)
            return {"success": True, "results": results[:10], "explanation": explanation}
        except Exception as e:
            return {"success": False, "error": f"Codebase search failed: {str(e)}"}

    def read_file(
        self,
        target_file: str,
        explanation: str = "",
        should_read_entire_file: bool = True,
        start_line_one_indexed: int = 1,
        end_line_one_indexed_inclusive: int = -1,
    ) -> dict:
        """Read contents of a file with line range support"""
        try:
            target_path = Path(target_file)
            if "tasks" in target_path.parts or target_path.name == "run_tests.sh":
                return {
                    "success": False,
                    "error": "Access denied: Reading files in 'tasks/' directory or 'run_tests.sh' is restricted.",
                    "target_file": target_file,
                }

            if self.container:
                result = run_command_in_container(
                    container=self.container,
                    command=["cat", str(self.base_path / target_file)],
                )
                if result["success"]:
                    content = result["output"]
                else:
                    return {
                        "success": False,
                        "error": f"Failed to read file: {result.get('error', 'Unknown error')}",
                    }
            else:
                # Local file system
                full_path = self.base_path / target_file
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

            lines = content.split("\n")
            total_lines = len(lines)

            if should_read_entire_file:
                return {
                    "success": True,
                    "content": content,
                    "target_file": target_file,
                    "total_lines": total_lines,
                    "explanation": explanation,
                }
            else:
                # Handle line range reading
                start_idx = max(0, start_line_one_indexed - 1)
                end_idx = (
                    min(total_lines, end_line_one_indexed_inclusive)
                    if end_line_one_indexed_inclusive != -1
                    else total_lines
                )

                selected_lines = lines[start_idx:end_idx]
                selected_content = "\n".join(selected_lines)

                return {
                    "success": True,
                    "content": selected_content,
                    "target_file": target_file,
                    "start_line": start_line_one_indexed,
                    "end_line": end_idx,
                    "total_lines": total_lines,
                    "lines_before": start_idx,
                    "lines_after": total_lines - end_idx,
                    "explanation": explanation,
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file '{target_file}': {str(e)}",
            }

    def run_terminal_cmd(
        self, command: str, explanation: str = "", is_background: bool = False
    ) -> dict:
        """Execute a terminal command"""
        try:
            if self.container:
                cmd_list = ["sh", "-c", command]
                result = run_command_in_container(
                    self.container, cmd_list, detach=is_background
                )
                return {
                    "success": result["success"],
                    "output": result.get("output", ""),
                    "error": result.get("error", ""),
                    "command": command,
                    "explanation": explanation,
                    "is_background": is_background,
                }
            else:
                # Local execution
                if is_background:
                    # For background processes, use Popen
                    process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        cwd=str(self.base_path),
                    )
                    return {
                        "success": True,
                        "message": f"Background process started with PID {process.pid}",
                        "pid": process.pid,
                        "command": command,
                        "explanation": explanation,
                        "is_background": True,
                    }
                else:
                    # Synchronous execution
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        cwd=str(self.base_path),
                        timeout=30,  # 30 second timeout
                    )
                    return {
                        "success": result.returncode == 0,
                        "output": result.stdout,
                        "error": result.stderr,
                        "return_code": result.returncode,
                        "command": command,
                        "explanation": explanation,
                        "is_background": False,
                    }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after 30 seconds: {command}",
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing command '{command}': {str(e)}",
                "command": command,
            }

    def list_dir(self, relative_workspace_path: str, explanation: str = "") -> dict:
        """List directory contents"""
        try:
            if self.container:
                # Normalize to a relative path within base_path
                safe_rel_path = relative_workspace_path.lstrip("/") or "."
                # Use shell to capture stderr as well (2>&1)
                list_cmd = f"ls -la {self.base_path / safe_rel_path} 2>&1"
                result = run_command_in_container(
                    container=self.container,
                    command=["sh", "-c", list_cmd],
                )
                if result["success"]:
                    return {
                        "success": True,
                        "contents": result["output"],
                        "path": safe_rel_path,
                        "explanation": explanation,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to list directory: {result.get('output') or 'Unknown error'}",
                        "path": safe_rel_path,
                        "command": list_cmd,
                    }
            else:
                # Local file system
                safe_rel_path = relative_workspace_path.lstrip("/") or "."
                full_path = self.base_path / safe_rel_path
                if full_path.exists() and full_path.is_dir():
                    contents = []
                    for item in full_path.iterdir():
                        stat_info = item.stat()
                        contents.append(
                            {
                                "name": item.name,
                                "type": "directory" if item.is_dir() else "file",
                                "size": stat_info.st_size if item.is_file() else None,
                                "permissions": oct(stat_info.st_mode)[-3:],
                            }
                        )
                    return {
                        "success": True,
                        "contents": contents,
                        "path": safe_rel_path,
                        "explanation": explanation,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Directory '{safe_rel_path}' does not exist or is not a directory",
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing directory '{relative_workspace_path}': {str(e)}",
            }

    def grep_search(
        self,
        query: str,
        explanation: str = "",
        case_sensitive: bool = False,
        include_pattern: str = None,
        exclude_pattern: str = None,
    ) -> dict:
        """Search for text patterns using grep/ripgrep"""
        try:
            # Build search command
            if self.container:

                # Check if ripgrep is available inside the container, fallback to grep.
                # rg_check = run_command_in_container(self.container, ["which", "rg"])
                # cmd = ["rg"] if rg_check["success"] else ["grep", "-r"]
                cmd = ["rg"]

                if not case_sensitive and cmd[0] == "rg":
                    cmd.append("-i")
                elif not case_sensitive and cmd[0] == "grep":
                    cmd.append("-i")

                default_excludes = [
                    "node_modules", ".venv", "venv", "__pycache__", ".git",
                    "dist", "build", "target", "vendor", ".next", ".nuxt",
                    ".cache", "tmp", "temp", ".gradle", ".m2", "obj", "bin"
                ]

                if cmd[0] == "rg":
                    for exc in default_excludes:
                        cmd.extend(["-g", f"!{exc}/"])
                else:
                    for exc in default_excludes:
                        cmd.extend(["--exclude-dir", exc])

                if include_pattern:
                    if cmd[0] == "rg":
                        cmd.extend(["-g", include_pattern])
                    else:
                        cmd.extend(["--include", include_pattern])

                if exclude_pattern:
                    if cmd[0] == "rg":
                        cmd.extend(["-g", f"!{exclude_pattern}"])
                    else:
                        cmd.extend(["--exclude", exclude_pattern])

                cmd.extend([query, str(self.base_path)])

                result = run_command_in_container(self.container, cmd)
                return {
                    "success": result["success"],
                    "matches": result.get("output", "").split("\n")
                    if result["success"]
                    else [],
                    "query": query,
                    "explanation": explanation,
                }
            else:
                # Local search
                cmd = ["rg"] if shutil.which("rg") else ["grep", "-r"]

                if not case_sensitive:
                    cmd.append("-i")

                default_excludes = [
                    "node_modules", ".venv", "venv", "__pycache__", ".git",
                    "dist", "build", "target", "vendor", ".next", ".nuxt",
                    ".cache", "tmp", "temp", ".gradle", ".m2", "obj", "bin"
                ]

                if cmd[0] == "rg":
                    for exc in default_excludes:
                        cmd.extend(["-g", f"!{exc}/"])
                else:
                    for exc in default_excludes:
                        cmd.extend(["--exclude-dir", exc])

                if include_pattern and cmd[0] == "rg":
                    cmd.extend(["-g", include_pattern])
                elif include_pattern and cmd[0] == "grep":
                    cmd.extend(["--include", include_pattern])

                if exclude_pattern and cmd[0] == "rg":
                    cmd.extend(["-g", f"!{exclude_pattern}"])
                elif exclude_pattern and cmd[0] == "grep":
                    cmd.extend(["--exclude", exclude_pattern])

                cmd.extend([query, str(self.base_path)])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                matches = result.stdout.split("\n") if result.stdout else []

                return {
                    "success": result.returncode == 0,
                    "matches": [m for m in matches if m.strip()],
                    "query": query,
                    "explanation": explanation,
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Grep search failed: {str(e)}",
                "query": query,
            }

    def edit_file(
        self,
        target_file: str,
        instructions: str,
        edit_type: str = "line_edits",
        line_edits: list = None,
    ) -> dict:
        """
        Edit a file using structured line-based editing

        Args:
            target_file: Path to the file to edit
            instructions: Description of the edit
            edit_type: Must be 'line_edits' (only supported type)
            line_edits: List of line-based edits
        """
        try:
            # Prevent editing test files
            if is_test_file_or_directory(target_file):
                return {
                    "success": False,
                    "error": f"Cannot edit test file '{target_file}'. Test files and directories are read-only to maintain evaluation integrity. Please modify source code files instead.",
                    "target_file": target_file,
                }

            if edit_type != "line_edits":
                return {
                    "success": False,
                    "error": f"Only 'line_edits' edit_type is supported, got: {edit_type}",
                }

            if self.container:
                # Handle container-based file operations
                container_file_path = str(self.base_path / target_file)

                # Check if file exists in container, create if needed
                check_result = run_command_in_container(
                    self.container, ["test", "-f", container_file_path]
                )

                if not check_result["success"]:
                    # File doesn't exist, create parent directories and file
                    parent_dir = str(Path(container_file_path).parent)
                    run_command_in_container(
                        self.container, ["mkdir", "-p", parent_dir]
                    )
                    run_command_in_container(
                        self.container, ["touch", container_file_path]
                    )

                return self._apply_line_edits(
                    container_file_path, line_edits, instructions
                )
            else:
                # Local filesystem operations
                file_path = self.base_path / target_file

                # Check if file exists, create parent directories if needed
                if not file_path.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    # Create empty file if it doesn't exist
                    file_path.touch()

                return self._apply_line_edits(file_path, line_edits, instructions)

        except Exception as e:
            return {
                "success": False,
                "error": f"File edit failed: {str(e)}",
                "target_file": target_file,
            }


    def _apply_line_edits(self, file_path, line_edits: list, instructions: str) -> dict:
        """Apply a list of line-based edits to a file"""
        try:
            if not line_edits:
                return {
                    "success": False,
                    "error": "line_edits is required for line_edits edit type",
                }

            # Read current file content
            if self.container:
                # Container-based file reading
                read_result = run_command_in_container(
                    self.container, ["cat", file_path]
                )
                if read_result["success"]:
                    content = read_result["output"]
                    lines = content.splitlines(keepends=True) if content else []
                else:
                    lines = []  # File doesn't exist or can't be read
            else:
                # Local file reading
                file_path_obj = (
                    file_path if isinstance(file_path, Path) else Path(file_path)
                )
                if file_path_obj.exists():
                    with open(file_path_obj, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                else:
                    lines = []

            # Process edits in a way that handles line number shifts correctly
            # Sort by line number, but handle different operations appropriately
            changes_made = []

            # Keep a copy of original content to detect no-op edits
            original_content = "".join(lines)

            # Group edits by type for better handling
            deletes = [e for e in line_edits if e.get("type") == "delete"]
            replaces = [e for e in line_edits if e.get("type") == "replace"]
            inserts = [e for e in line_edits if e.get("type") == "insert"]

            # Apply deletes first (in reverse line order)
            for edit in sorted(
                deletes, key=lambda x: x.get("line_number", 0), reverse=True
            ):
                line_number = edit.get("line_number", 1)
                line_idx = max(0, line_number - 1)

                if line_idx < len(lines):
                    deleted_content = lines[line_idx].rstrip("\n")
                    del lines[line_idx]
                    changes_made.append(
                        f"Line {line_number}: Deleted '{deleted_content[:50]}...'"
                    )
                else:
                    changes_made.append(
                        f"Line {line_number}: Could not delete (line doesn't exist)"
                    )

            # Apply replaces (in reverse line order)
            for edit in sorted(
                replaces, key=lambda x: x.get("line_number", 0), reverse=True
            ):
                line_number = edit.get("line_number", 1)
                content = edit.get("content", "")
                line_idx = max(0, line_number - 1)

                if line_idx < len(lines):
                    old_content = lines[line_idx].rstrip("\n")
                    lines[line_idx] = content + "\n"
                    changes_made.append(
                        f"Line {line_number}: Replaced '{old_content[:50]}...' with '{content[:50]}...'"
                    )
                else:
                    # Line doesn't exist, extend the file to that line
                    while len(lines) < line_number:
                        lines.append("\n")
                    lines[line_number - 1] = content + "\n"
                    changes_made.append(
                        f"Line {line_number}: Added '{content[:50]}...' (extended file)"
                    )

            # Apply inserts (in reverse line order to avoid shifting issues)
            for edit in sorted(
                inserts, key=lambda x: x.get("line_number", 0), reverse=True
            ):
                line_number = edit.get("line_number", 1)
                content = edit.get("content", "")
                line_idx = max(0, line_number - 1)

                # Insert at the specified position
                if line_idx <= len(lines):
                    lines.insert(line_idx, content + "\n")
                    changes_made.append(
                        f"Line {line_number}: Inserted '{content[:50]}...'"
                    )
                else:
                    # Beyond end of file, just append
                    lines.append(content + "\n")
                    changes_made.append(
                        f"Line {line_number}: Appended '{content[:50]}...' (beyond file end)"
                    )

            # Validate Python syntax if this is a Python file
            content = "".join(lines)

            # Detect no-op edit (no effective change in file text)
            if content == original_content:
                return {
                    "success": False,
                    "error": "No effective change (new content identical to existing file)",
                    "target_file": str(Path(file_path).relative_to(Path(self.base_path))) if hasattr(self, 'base_path') else str(file_path),
                    "instructions": instructions,
                    "total_edits": len(line_edits),
                }
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.py':
                try:
                    import ast
                    ast.parse(content)
                    print(f"HARNESS: Python syntax validation passed for {file_path}")
                except SyntaxError as e:
                    error_msg = f"Python syntax error in {file_path}: {e.msg} at line {e.lineno}"
                    print(f"HARNESS: {error_msg}")
                    print(f"HARNESS: Changes that would have been applied: {changes_made}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "target_file": str(Path(file_path).relative_to(Path(self.base_path))) if hasattr(self, 'base_path') else str(file_path),
                        "syntax_error": True,
                        "syntax_line": e.lineno,
                        "syntax_msg": e.msg,
                        "attempted_changes": changes_made
                    }
                except Exception as e:
                    print(f"HARNESS: Could not validate Python syntax: {e}")

            # Write the modified content back to file
            if self.container:
                # Enhanced container-based file writing with better error handling
                print(f"HARNESS: Writing {len(content)} characters to {file_path}")

                # Method 1: Try python-based writing first (most reliable)
                import base64
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
                python_write_cmd = [
                    "python3", "-c",
                    f"import base64; "
                    f"content = base64.b64decode('{encoded_content}').decode('utf-8'); "
                    f"open('{file_path}', 'w', encoding='utf-8').write(content)"
                ]
                write_result = run_command_in_container(self.container, python_write_cmd)

                if not write_result["success"]:
                    print(f"HARNESS: Python write failed, trying cat method...")
                    # Fallback: Use cat with proper content handling
                    # Create a temporary file with safe content then copy it
                    import tempfile
                    import shlex

                    # Write to a temporary file path that's safe
                    temp_path = f"/tmp/edit_content_{hash(content) % 10000}.tmp"
                    escaped_content = content.replace("'", "'\"'\"'")  # Escape single quotes properly
                    cat_cmd = ["sh", "-c", f"cat > {temp_path} << 'EDIT_EOF'\n{escaped_content}\nEDIT_EOF\n && mv {temp_path} {file_path}"]

                    write_result = run_command_in_container(self.container, cat_cmd)

                if not write_result["success"]:
                    print(f"HARNESS: Both write methods failed!")
                    print(f"HARNESS: Write error: {write_result.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": f"Failed to write file to container: {write_result.get('error', 'Unknown error')}",
                        "target_file": str(
                            Path(file_path).relative_to(Path(self.base_path))
                        ),
                    }

                print(f"HARNESS: File write succeeded, verifying content...")

                # Enhanced verification with detailed comparison
                verify_read = run_command_in_container(self.container, ["cat", file_path])
                if not verify_read.get("success"):
                    print(f"HARNESS: Verification read failed: {verify_read.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": f"Failed to read file back for verification: {verify_read.get('error', 'Unknown error')}",
                        "target_file": str(
                            Path(file_path).relative_to(Path(self.base_path))
                        ),
                    }

                # Normalize for trailing newline and CRLF vs LF differences
                def _norm(s: str) -> str:
                    return s.replace("\r\n", "\n").rstrip("\n")

                written_content = verify_read.get("output", "")
                expected_normalized = _norm(content)
                actual_normalized = _norm(written_content)

                if actual_normalized != expected_normalized:
                    print(f"HARNESS: Content verification failed!")
                    print(f"HARNESS: Expected length: {len(expected_normalized)}")
                    print(f"HARNESS: Actual length: {len(actual_normalized)}")
                    print(f"HARNESS: Expected: {expected_normalized}")
                    print(f"HARNESS: Actual: {actual_normalized}")
                    return {
                        "success": False,
                        "error": "Write verification failed (content mismatch after write)",
                        "target_file": str(
                            Path(file_path).relative_to(Path(self.base_path))
                        ),
                        "expected_length": len(expected_normalized),
                        "actual_length": len(actual_normalized),
                    }

                print(f"HARNESS: Content verification passed!")

                # Stage changes to make them visible to diff tools
                print(f"HARNESS: Staging changes with git...")
                git_add_result = run_command_in_container(
                    self.container,
                    ["git", "-C", "/app", "add", "-A"],
                )

                if not git_add_result.get("success"):
                    print(f"HARNESS: Git add failed: {git_add_result.get('error', 'Unknown error')}")

                # Check git status for debugging
                git_status_result = run_command_in_container(
                    self.container,
                    ["git", "-C", "/app", "status", "--porcelain"],
                )
                if git_status_result.get("success"):
                    print(f"HARNESS: Git status after edit: {git_status_result.get('output', '').strip()}")

                # Log staged changes for visibility
                staged_names = run_command_in_container(
                    self.container,
                    ["git", "-C", "/app", "diff", "--cached", "--name-only"],
                )
                if staged_names.get("success"):
                    print(f"HARNESS: Staged files after edit: {staged_names.get('output', '').strip()}")
                else:
                    print(f"HARNESS: Failed to check staged files: {staged_names.get('error', 'Unknown error')}")

                file_name = Path(file_path).name
                target_file = str(Path(file_path).relative_to(Path(self.base_path)))
            else:
                # Local file writing
                file_path_obj = (
                    file_path if isinstance(file_path, Path) else Path(file_path)
                )
                with open(file_path_obj, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                # Verify persistence locally
                with open(file_path_obj, "r", encoding="utf-8") as f:
                    read_back = f.read()
                    def _norm_local(s: str) -> str:
                        return s.replace("\r\n", "\n").rstrip("\n")
                    if _norm_local(read_back) != _norm_local(content):
                        return {
                            "success": False,
                            "error": "Write verification failed (content mismatch after write)",
                            "target_file": str(file_path_obj.relative_to(self.base_path)),
                        }

                file_name = file_path_obj.name
                target_file = str(file_path_obj.relative_to(self.base_path))

            return {
                "success": True,
                "message": f"Successfully applied {len(line_edits)} line edits to {file_name}",
                "target_file": target_file,
                "instructions": instructions,
                "changes_made": changes_made,
                "total_edits": len(line_edits),
            }

        except Exception as e:
            target_file = (
                str(Path(file_path).relative_to(Path(self.base_path)))
                if isinstance(file_path, str)
                else str(file_path.relative_to(self.base_path))
            )
            return {
                "success": False,
                "error": f"Error applying line edits: {str(e)}",
                "target_file": target_file,
            }

    def search_replace(self, file_path: str, old_string: str, new_string: str) -> dict:
        """Search and replace text in a file"""
        try:
            # Prevent modifying test files
            if is_test_file_or_directory(file_path):
                return {
                    "success": False,
                    "error": f"Cannot modify test file '{file_path}'. Test files and directories are read-only to maintain evaluation integrity.",
                    "file_path": file_path,
                }

            if self.container:
                # Read file first
                read_result = run_command_in_container(
                    self.container, ["cat", str(self.base_path / file_path)]
                )
                if not read_result["success"]:
                    return {
                        "success": False,
                        "error": f"Failed to read file: {read_result.get('error', 'Unknown error')}",
                    }

                content = read_result["output"]

                # Perform replacement
                if old_string in content:
                    new_content = content.replace(
                        old_string, new_string, 1
                    )  # Replace only first occurrence

                    # Write back to file
                    escaped_content = new_content.replace('"', '\\"').replace(
                        "$", "\\$"
                    )
                    write_result = run_command_in_container(
                        self.container,
                        [
                            "sh",
                            "-c",
                            f'echo "{escaped_content}" > {self.base_path / file_path}',
                        ],
                    )

                    return {
                        "success": write_result["success"],
                        "message": f"Successfully replaced text in {file_path}",
                        "file_path": file_path,
                        "old_string": old_string,
                        "new_string": new_string,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Old string not found in file {file_path}",
                        "file_path": file_path,
                    }
            else:
                # Local file system
                full_path = self.base_path / file_path
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if old_string in content:
                    new_content = content.replace(
                        old_string, new_string, 1
                    )  # Replace only first occurrence

                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    return {
                        "success": True,
                        "message": f"Successfully replaced text in {file_path}",
                        "file_path": file_path,
                        "old_string": old_string,
                        "new_string": new_string,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Old string not found in file {file_path}",
                        "file_path": file_path,
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Search and replace failed: {str(e)}",
                "file_path": file_path,
            }

    def file_search(self, query: str, explanation: str = "") -> dict:
        """Search for files by name using fuzzy matching"""
        try:
            results = []
            if self.container:
                # Use find command to search for files
                cmd = ["find", str(self.base_path), "-name", f"*{query}*", "-type", "f"]
                result = run_command_in_container(self.container, cmd)
                if result["success"]:
                    files = [
                        f.strip() for f in result["output"].split("\n") if f.strip()
                    ]
                    for file in files[:10]:  # Limit to 10 results
                        rel_path = (
                            Path(file).relative_to(self.base_path)
                            if str(self.base_path) in file
                            else file
                        )
                        results.append(str(rel_path))
            else:
                # Local fuzzy search
                search_path = self.base_path
                for file in search_path.rglob("*"):
                    if file.is_file() and query.lower() in file.name.lower():
                        results.append(str(file.relative_to(self.base_path)))
                        if len(results) >= 10:  # Limit results
                            break

            return {
                "success": True,
                "results": results,
                "query": query,
                "explanation": explanation,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"File search failed: {str(e)}",
                "query": query,
            }

    def delete_file(self, target_file: str, explanation: str = "") -> dict:
        """Delete a file"""
        try:
            # Prevent deleting test files
            if is_test_file_or_directory(target_file):
                return {
                    "success": False,
                    "error": f"Cannot delete test file '{target_file}'. Test files and directories are read-only to maintain evaluation integrity.",
                    "target_file": target_file,
                }

            if self.container:
                result = run_command_in_container(
                    self.container, ["rm", str(self.base_path / target_file)]
                )
                return {
                    "success": result["success"],
                    "message": f"File {target_file} deleted"
                    if result["success"]
                    else "Failed to delete file",
                    "target_file": target_file,
                    "explanation": explanation,
                    "error": result.get("error") if not result["success"] else None,
                }
            else:
                # Local file deletion
                full_path = self.base_path / target_file
                if full_path.exists():
                    full_path.unlink()
                    return {
                        "success": True,
                        "message": f"File {target_file} deleted successfully",
                        "target_file": target_file,
                        "explanation": explanation,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"File {target_file} does not exist",
                        "target_file": target_file,
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete file {target_file}: {str(e)}",
                "target_file": target_file,
            }

    def web_search(self, search_term: str, explanation: str = "") -> dict:
        """NOT IMPLEMENTED"""
        return {
            "success": False,
            "error": "NotImplemented: Web search functionality is not available in this environment",
            "search_term": search_term,
            "explanation": explanation
        }

    def create_diagram(self, content: str) -> dict:
        """NOT IMPLEMENTED"""
        return {
            "success": False,
            "error": "NotImplemented: Diagram creation functionality is not available in this environment",
            "content": content
        }

    def edit_notebook(
        self,
        target_notebook: str,
        cell_idx: int,
        is_new_cell: bool,
        cell_language: str,
        old_string: str,
        new_string: str,
    ) -> dict:
        """Edit a Jupyter notebook cell with full .ipynb support"""
        try:
            import json

            # Read the notebook file
            if self.container:
                result = run_command_in_container(
                    container=self.container,
                    command=["cat", str(self.base_path / target_notebook)]
                )
                if not result["success"]:
                    return {
                        "success": False,
                        "error": f"Failed to read notebook: {result.get('error', 'Unknown error')}"
                    }
                notebook_content = result["output"]
            else:
                try:
                    with open(self.base_path / target_notebook, 'r', encoding='utf-8') as f:
                        notebook_content = f.read()
                except FileNotFoundError:
                    # Create new notebook if it doesn't exist
                    notebook_content = json.dumps({
                        "cells": [],
                        "metadata": {},
                        "nbformat": 4,
                        "nbformat_minor": 4
                    })

            # Parse the notebook JSON
            try:
                notebook = json.loads(notebook_content)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid notebook JSON: {str(e)}"
                }

            # Ensure cells array exists
            if "cells" not in notebook:
                notebook["cells"] = []

            # Determine cell type
            cell_type = "code" if cell_language == "python" else "markdown"
            if cell_language in ["python", "javascript", "typescript", "r", "sql", "shell"]:
                cell_type = "code"
            elif cell_language in ["markdown", "raw"]:
                cell_type = cell_language

            if is_new_cell:
                # Create new cell
                new_cell = {
                    "cell_type": cell_type,
                    "metadata": {},
                    "source": new_string.split('\n') if new_string else [""]
                }

                if cell_type == "code":
                    new_cell["execution_count"] = None
                    new_cell["outputs"] = []

                # Insert at specified index
                if cell_idx <= len(notebook["cells"]):
                    notebook["cells"].insert(cell_idx, new_cell)
                else:
                    notebook["cells"].append(new_cell)

                action = f"Created new {cell_type} cell at index {cell_idx}"
            else:
                # Edit existing cell
                if cell_idx >= len(notebook["cells"]):
                    return {
                        "success": False,
                        "error": f"Cell index {cell_idx} out of range (notebook has {len(notebook['cells'])} cells)"
                    }

                cell = notebook["cells"][cell_idx]
                current_source = "\n".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]

                if old_string in current_source:
                    new_source = current_source.replace(old_string, new_string)
                    cell["source"] = new_source.split('\n')
                    action = f"Edited cell {cell_idx}"
                else:
                    return {
                        "success": False,
                        "error": f"Old string not found in cell {cell_idx}"
                    }

            # Write back the notebook
            updated_content = json.dumps(notebook, indent=2)

            if self.container:
                # Escape content for shell
                escaped_content = updated_content.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                result = run_command_in_container(
                    container=self.container,
                    command=["sh", "-c", f'echo "{escaped_content}" > {self.base_path / target_notebook}']
                )
                write_success = result["success"]
            else:
                try:
                    with open(self.base_path / target_notebook, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    write_success = True
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to write notebook: {str(e)}"
                    }

            if write_success:
                return {
                    "success": True,
                    "message": action,
                    "target_notebook": target_notebook,
                    "cell_idx": cell_idx,
                    "cell_type": cell_type,
                    "is_new_cell": is_new_cell,
                    "total_cells": len(notebook["cells"])
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to write notebook file"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error editing notebook: {str(e)}",
                "target_notebook": target_notebook
            }

    def write_file(self, file_path: str, content: str) -> dict:
        """Write content to a file - kept for backward compatibility"""
        try:
            # Prevent writing to test files
            if is_test_file_or_directory(file_path):
                return {
                    "success": False,
                    "error": f"Cannot write to test file '{file_path}'. Test files and directories are read-only to maintain evaluation integrity.",
                    "file_path": file_path,
                }

            if self.container:
                # Use echo to write content to file in container
                escaped_content = content.replace('"', '\\"').replace("$", "\\$")
                result = run_command_in_container(
                    container=self.container,
                    command=[
                        "sh",
                        "-c",
                        f'echo "{escaped_content}" > {self.base_path / file_path}',
                    ],
                )
                return {
                    "success": result["success"],
                    "message": f"Successfully wrote to {file_path}"
                    if result["success"]
                    else "Failed to write file",
                    "file_path": file_path,
                    "error": result.get("error") if not result["success"] else None,
                }
            else:
                # Local file system
                full_path = self.base_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {
                    "success": True,
                    "message": f"Successfully wrote to {file_path}",
                    "file_path": file_path,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error writing file '{file_path}': {str(e)}",
            }

    def list_files(self, directory: str = ".") -> dict:
        """List files in a directory - kept for backward compatibility"""
        try:
            if self.container:
                result = run_command_in_container(
                    container=self.container,
                    command=[
                        "find",
                        str(self.base_path / directory),
                        "-type",
                        "f",
                        # JavaScript/Node.js
                        "-not", "-path", "*/node_modules/*",
                        "-not", "-path", "*/.next/*",
                        "-not", "-path", "*/.nuxt/*",
                        "-not", "-path", "*/dist/*",
                        "-not", "-path", "*/build/*",

                        # Python
                        "-not", "-path", "*/__pycache__/*",
                        "-not", "-path", "*/.venv/*",
                        "-not", "-path", "*/venv/*",
                        "-not", "-path", "*/.env/*",
                        "-not", "-path", "*/site-packages/*",
                        "-not", "-path", "*/.tox/*",
                        "-not", "-path", "*/.pytest_cache/*",
                        "-not", "-path", "*/.mypy_cache/*",
                        "-not", "-path", "*.egg-info/*",

                        # Ruby
                        "-not", "-path", "*/vendor/bundle/*",
                        "-not", "-path", "*/.bundle/*",

                        # Java/Kotlin/Gradle/Maven
                        "-not", "-path", "*/target/*",
                        "-not", "-path", "*/.gradle/*",
                        "-not", "-path", "*/.m2/*",

                        # .NET/C#
                        "-not", "-path", "*/bin/*",
                        "-not", "-path", "*/obj/*",
                        "-not", "-path", "*/packages/*",

                        # Go
                        "-not", "-path", "*/vendor/*",

                        # Rust
                        "-not", "-path", "*/target/debug/*",
                        "-not", "-path", "*/target/release/*",

                        # PHP
                        "-not", "-path", "*/vendor/*",

                        # Misc
                        "-not", "-path", "*/.git/*",
                        "-not", "-path", "*/.svn/*",
                        "-not", "-path", "*/.hg/*",
                        "-not", "-path", "*/.vscode/*",
                        "-not", "-path", "*/.idea/*",
                        "-not", "-path", "*/.vs/*",
                        "-not", "-path", "*/.cache/*",
                        "-not", "-path", "*/tmp/*",
                        "-not", "-path", "*/temp/*",
                        "-not", "-path", "*/.tmp/*",
                        "-not", "-path", "*/.terraform/*",
                        "-not", "-path", "*/.docker/*",
                        "-name",
                        "*",
                    ],
                )
                if result["success"]:
                    files = [
                        line.strip()
                        for line in result["output"].split("\n")
                        if line.strip()
                    ]
                    relative_files = []
                    for file in files:
                        try:
                            rel_path = Path(file).relative_to(self.base_path)
                            relative_files.append(str(rel_path))
                        except ValueError:
                            relative_files.append(file)
                    return {
                        "success": True,
                        "files": relative_files,
                        "directory": directory,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to list files: {result.get('error', 'Unknown error')}",
                    }
            else:
                # Local file system
                full_path = self.base_path / directory
                if full_path.exists() and full_path.is_dir():
                    exclude_patterns = [
                        'node_modules', '.next', '.nuxt', 'dist', 'build',
                        '__pycache__', '.venv', 'venv', '.env', 'site-packages',
                        '.tox', '.pytest_cache', '.mypy_cache', '.egg-info',
                        'vendor/bundle', '.bundle', 'target', '.gradle', '.m2',
                        'bin', 'obj', 'packages', 'vendor',
                        '.git', '.svn', '.hg',
                        '.vscode', '.idea', '.vs',
                        '.cache', 'tmp', 'temp', '.tmp',
                        '.terraform', '.docker'
                    ]

                    def should_exclude(path: Path) -> bool:
                        """Check if path contains any excluded directory"""
                        path_parts = path.parts
                        return any(pattern in path_parts for pattern in exclude_patterns)

                    files = [
                        str(p.relative_to(self.base_path))
                        for p in full_path.rglob("*")
                        if p.is_file() and not should_exclude(p)
                    ]
                    return {"success": True, "files": files, "directory": directory}
                else:
                    return {
                        "success": False,
                        "error": f"Directory '{directory}' does not exist",
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing files in '{directory}': {str(e)}",
            }

    def create_directory(self, directory_path: str) -> dict:
        """Create a directory - kept for backward compatibility"""
        try:
            if self.container:
                result = run_command_in_container(
                    container=self.container,
                    command=["mkdir", "-p", str(self.base_path / directory_path)],
                )
                return {
                    "success": result["success"],
                    "message": f"Successfully created directory {directory_path}"
                    if result["success"]
                    else "Failed to create directory",
                    "directory_path": directory_path,
                    "error": result.get("error") if not result["success"] else None,
                }
            else:
                # Local file system
                full_path = self.base_path / directory_path
                full_path.mkdir(parents=True, exist_ok=True)
                return {
                    "success": True,
                    "message": f"Successfully created directory {directory_path}",
                    "directory_path": directory_path,
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating directory '{directory_path}': {str(e)}",
            }

    def api_call(self, method: str, url: str, headers: dict = None, body: dict = None, explanation: str = "") -> dict:
        """Make HTTP API calls to test backend functionality"""
        try:
            import urllib.request
            import urllib.parse
            import json

            # Handle relative URLs
            if not url.startswith("http"):
                url = f"{self.mern_config['api_base_url']}{url if url.startswith('/') else '/' + url}"

            # Prepare request
            req_headers = headers or {}
            req_headers.setdefault("Content-Type", "application/json")

            request_data = None
            if body and method in ["POST", "PUT", "PATCH"]:
                request_data = json.dumps(body).encode('utf-8')

            req = urllib.request.Request(url, data=request_data, headers=req_headers, method=method)

            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    response_data = response.read().decode('utf-8')
                    try:
                        json_data = json.loads(response_data)
                    except json.JSONDecodeError:
                        json_data = response_data

                    return {
                        "success": True,
                        "status_code": response.status,
                        "data": json_data,
                        "url": url,
                        "method": method,
                        "explanation": explanation
                    }
            except urllib.error.HTTPError as e:
                error_data = e.read().decode('utf-8')
                try:
                    error_json = json.loads(error_data)
                except json.JSONDecodeError:
                    error_json = error_data

                return {
                    "success": False,
                    "status_code": e.code,
                    "error": error_json,
                    "url": url,
                    "method": method,
                    "explanation": explanation
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"API call failed: {str(e)}",
                "url": url,
                "method": method,
                "explanation": explanation
            }

    def database_query(self, query_type: str, collection: str, query: dict = None, data: dict = None, explanation: str = "") -> dict:
        """Execute MongoDB queries to test data persistence"""
        try:
            # Try using pymongo if available
            try:
                from pymongo import MongoClient

                client = MongoClient(self.mern_config['mongo_uri'])
                db = client.get_default_database()
                coll = db[collection]

                result = None
                if query_type == "find":
                    result = list(coll.find(query or {}))
                elif query_type == "insert":
                    result = coll.insert_one(data or {})
                    result = {"inserted_id": str(result.inserted_id)}
                elif query_type == "update":
                    result = coll.update_many(query or {}, {"$set": data or {}})
                    result = {"matched_count": result.matched_count, "modified_count": result.modified_count}
                elif query_type == "delete":
                    result = coll.delete_many(query or {})
                    result = {"deleted_count": result.deleted_count}
                elif query_type == "aggregate":
                    result = list(coll.aggregate(query or []))

                client.close()
                return {
                    "success": True,
                    "result": result,
                    "collection": collection,
                    "query_type": query_type,
                    "explanation": explanation
                }

            except ImportError:
                # Fallback: use mongosh command if pymongo not available
                if self.container:
                    mongo_cmd = f"mongosh {self.mern_config['mongo_uri']} --eval 'db.{collection}.{query_type}({json.dumps(query or {})})''"
                    result = run_command_in_container(self.container, ["sh", "-c", mongo_cmd])
                    return {
                        "success": result["success"],
                        "result": result.get("output", ""),
                        "collection": collection,
                        "query_type": query_type,
                        "explanation": explanation
                    }
                else:
                    return {
                        "success": False,
                        "error": "PyMongo not available and not in container environment",
                        "explanation": explanation
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Database query failed: {str(e)}",
                "collection": collection,
                "query_type": query_type,
                "explanation": explanation
            }

    def websocket_test(self, event_name: str, event_data: dict = None, expected_response: str = "", timeout: int = 10, explanation: str = "") -> dict:
        """Test WebSocket/Socket.IO functionality"""
        try:
            # Try using socketio client if available
            try:
                import socketio

                sio = socketio.SimpleClient()
                sio.connect(self.mern_config['websocket_url'])

                # Send event
                sio.emit(event_name, event_data or {})

                # Wait for response if expected
                if expected_response:
                    try:
                        response = sio.receive(timeout=timeout)
                        sio.disconnect()
                        return {
                            "success": True,
                            "event_sent": event_name,
                            "response_received": response,
                            "explanation": explanation
                        }
                    except Exception as e:
                        sio.disconnect()
                        return {
                            "success": False,
                            "error": f"No response received: {str(e)}",
                            "event_sent": event_name,
                            "explanation": explanation
                        }
                else:
                    sio.disconnect()
                    return {
                        "success": True,
                        "event_sent": event_name,
                        "message": "Event sent successfully (no response expected)",
                        "explanation": explanation
                    }

            except ImportError:
                # Fallback: simulate websocket test
                return {
                    "success": True,
                    "event_sent": event_name,
                    "message": "WebSocket test simulated (socketio client not available)",
                    "note": "Install python-socketio for real WebSocket testing",
                    "explanation": explanation
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"WebSocket test failed: {str(e)}",
                "event_name": event_name,
                "explanation": explanation
            }

    def ui_test(self, action: str, selector: str = "", text: str = "", url: str = "", timeout: int = 10, explanation: str = "") -> dict:
        """NOT IMPLEMENTED"""
        return {
            "success": False,
            "error": "NotImplemented: UI testing functionality is not available in this environment",
            "action": action,
            "selector": selector,
            "explanation": explanation
        }


class LiteLLMAgentHarness:
    """Enhanced agent harness with comprehensive tool capabilities using litellm"""

    def __init__(
        self,
        model_name: str = "claude-3-haiku-20240307",
        container=None,
        base_path: str = "/workspace",
        max_tokens: int = 4000,
        temperature: float = 0.1,
        mern_config: dict = None,
    ):
        self.model_name = model_name
        self.container = container
        self.base_path = base_path
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.enhanced_tools = EnhancedTools(container, base_path, mern_config)

        # Define available tools
        self.tools = [tool for tool in self.enhanced_tools.tools_info]

    def _execute_tool_call(self, tool_call) -> dict:
        """Execute a tool call and return the result"""
        function_name = tool_call.function.name
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in tool arguments: {str(e)}"}

        # Route to appropriate tool method
        if function_name == "codebase_search":
            return self.enhanced_tools.codebase_search(
                query=arguments["query"],
                explanation=arguments.get("explanation", ""),
                target_directories=arguments.get("target_directories"),
            )
        elif function_name == "read_file":
            return self.enhanced_tools.read_file(
                target_file=arguments["target_file"],
                explanation=arguments.get("explanation", ""),
                should_read_entire_file=arguments.get("should_read_entire_file", True),
                start_line_one_indexed=arguments.get("start_line_one_indexed", 1),
                end_line_one_indexed_inclusive=arguments.get(
                    "end_line_one_indexed_inclusive", -1
                ),
            )
        elif function_name == "run_terminal_cmd":
            return self.enhanced_tools.run_terminal_cmd(
                command=arguments["command"],
                explanation=arguments.get("explanation", ""),
                is_background=arguments.get("is_background", False),
            )
        elif function_name == "list_dir":
            return self.enhanced_tools.list_dir(
                relative_workspace_path=arguments["relative_workspace_path"],
                explanation=arguments.get("explanation", ""),
            )
        elif function_name == "grep_search":
            return self.enhanced_tools.grep_search(
                query=arguments["query"],
                explanation=arguments.get("explanation", ""),
                case_sensitive=arguments.get("case_sensitive", False),
                include_pattern=arguments.get("include_pattern"),
                exclude_pattern=arguments.get("exclude_pattern"),
            )
        elif function_name == "edit_file":
            return self.enhanced_tools.edit_file(
                target_file=arguments["target_file"],
                instructions=arguments["instructions"],
                edit_type=arguments.get("edit_type", "line_edits"),
                line_edits=arguments.get("line_edits"),
            )
        elif function_name == "search_replace":
            return self.enhanced_tools.search_replace(
                file_path=arguments["file_path"],
                old_string=arguments["old_string"],
                new_string=arguments["new_string"],
            )
        elif function_name == "file_search":
            return self.enhanced_tools.file_search(
                query=arguments["query"], explanation=arguments.get("explanation", "")
            )
        elif function_name == "delete_file":
            return self.enhanced_tools.delete_file(
                target_file=arguments["target_file"],
                explanation=arguments.get("explanation", ""),
            )
        elif function_name == "web_search":
            return self.enhanced_tools.web_search(
                search_term=arguments["search_term"],
                explanation=arguments.get("explanation", ""),
            )
        elif function_name == "create_diagram":
            return self.enhanced_tools.create_diagram(content=arguments["content"])
        elif function_name == "edit_notebook":
            return self.enhanced_tools.edit_notebook(
                target_notebook=arguments["target_notebook"],
                cell_idx=arguments["cell_idx"],
                is_new_cell=arguments["is_new_cell"],
                cell_language=arguments["cell_language"],
                old_string=arguments["old_string"],
                new_string=arguments["new_string"],
            )
        # Backward compatibility with old tool names
        elif function_name == "write_file":
            return self.enhanced_tools.write_file(
                arguments["file_path"], arguments["content"]
            )
        elif function_name == "list_files":
            directory = arguments.get("directory", ".")
            return self.enhanced_tools.list_files(directory)
        elif function_name == "create_directory":
            return self.enhanced_tools.create_directory(arguments["directory_path"])
        elif function_name == "api_call":
            return self.enhanced_tools.api_call(
                method=arguments["method"],
                url=arguments["url"],
                headers=arguments.get("headers"),
                body=arguments.get("body"),
                explanation=arguments.get("explanation", ""),
            )
        elif function_name == "database_query":
            return self.enhanced_tools.database_query(
                query_type=arguments["query_type"],
                collection=arguments["collection"],
                query=arguments.get("query"),
                data=arguments.get("data"),
                explanation=arguments.get("explanation", ""),
            )
        elif function_name == "websocket_test":
            return self.enhanced_tools.websocket_test(
                event_name=arguments["event_name"],
                event_data=arguments.get("event_data"),
                expected_response=arguments.get("expected_response", ""),
                timeout=arguments.get("timeout", 10),
                explanation=arguments.get("explanation", ""),
            )
        elif function_name == "ui_test":
            return self.enhanced_tools.ui_test(
                action=arguments["action"],
                selector=arguments.get("selector", ""),
                text=arguments.get("text", ""),
                url=arguments.get("url", ""),
                timeout=arguments.get("timeout", 10),
                explanation=arguments.get("explanation", ""),
            )
        else:
            return {"error": f"Unknown function: {function_name}"}

    def execute_task(self, task_prompt: str, max_iterations: int = 10) -> dict:
        """Execute a task using the agent with file editing capabilities"""
        messages = [
            {
                "role": "system",
                "content": """
You are a powerful coding assistant with comprehensive development capabilities. You have access to the following tools:

SEARCH & DISCOVERY:
- codebase_search: Semantic search through codebase to find relevant code snippets
- grep_search: Fast regex-based text search with file filtering
- file_search: Fuzzy search for files by name
- list_dir: List directory contents for exploration

FILE OPERATIONS:
- read_file: Read file contents with optional line range support
- edit_file: Propose structured edits to files
- search_replace: Find and replace text in files
- write_file: Create new files or overwrite existing ones
- delete_file: Remove files from the filesystem

EXECUTION & AUTOMATION:
- run_terminal_cmd: Execute shell commands (with background support)
- create_directory: Create directory structures

SPECIALIZED TOOLS:
- edit_notebook: Edit Jupyter notebook cells
- create_diagram: Generate Mermaid diagrams
- web_search: Search the web for information (when available)

MERN STACK TOOLS:
- api_call: Make HTTP requests to test REST API endpoints
- database_query: Execute MongoDB queries (find, insert, update, delete, aggregate)
- websocket_test: Test Socket.IO real-time functionality
- ui_test: Browser automation for React frontend testing (screenshot, click, type, navigate)

WORKFLOW GUIDELINES:
1. Break down complex tasks into steps
2. Use search tools to understand the codebase first
3. Read relevant files before making changes
4. Use appropriate tools for the task (semantic search vs grep vs file search)
5. Provide clear explanations with each tool use
6. Test changes when possible using terminal commands

FOR MERN STACK APPLICATIONS:
1. Identify if you're working with a MERN (MongoDB, Express, React, Node.js) stack
2. Use api_call to test backend endpoints after making changes
3. Use database_query to verify data persistence in MongoDB
4. Use websocket_test for real-time features (chat, notifications, live updates)
5. Use ui_test to verify frontend functionality and user interactions
6. Look for server/ directory (backend), client/ directory (frontend), and package.json files

Always explain your reasoning and approach clearly.
""",
            },
            {"role": "user", "content": task_prompt},
        ]

        iterations = 0
        conversation_history = []
        made_code_changes = False

        while iterations < max_iterations:
            iterations += 1

            try:
                print(f"HARNESS: Iteration {iterations}, making LLM call with model {self.model_name}")
                print(f"HARNESS: Messages length: {len(messages)}")
                print(f"HARNESS: Current conversation:")
                for i, msg in enumerate(messages[-3:], max(0, len(messages)-3)):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    if isinstance(content, str):
                        print(f"HARNESS: Message {i}: [{role}] {content}")
                    else:
                        print(f"HARNESS: Message {i}: [{role}] [Non-string content]")
                print(f"HARNESS: Tools available: {len(self.tools)}")

                # Context window management - simple message count limit
                if len(messages) > 25:  # Keep conversations manageable
                    print(f"HARNESS: Truncating conversation to fit context window")
                    # Keep system message and last 20 messages only
                    system_msg = messages[0]
                    recent_messages = messages[-20:]
                    messages = [system_msg] + recent_messages
                    print(f"HARNESS: Truncated to {len(messages)} messages")

                # Make the LLM call
                # Safety settings for Gemini to prevent blocking
                extra_params = {}
                if "gemini" in self.model_name.lower():
                    extra_params["safety_settings"] = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]

                response = completion(
                    model=self.model_name,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=300,  # 5 minute timeout per API call
                    **extra_params,
                )
                print(f"HARNESS: LLM API call succeeded, processing response...")
                message = response.choices[0].message

                if "gemini" in self.model_name.lower() and message.content is None:
                    message.content = ""

                messages.append(message.dict())

                print(f"HARNESS: Got response:")
                print(f"HARNESS: Response content: {message.content or '[No content]'}")
                print(f"HARNESS: Tool calls: {len(message.tool_calls) if message.tool_calls else 0}")

                if message.tool_calls:
                    for i, tool_call in enumerate(message.tool_calls, 1):
                        print(f"HARNESS: Tool call {i}: {tool_call.function.name}")
                        try:
                            args = json.loads(tool_call.function.arguments)
                            print(f"HARNESS: Tool call {i} arguments: {json.dumps(args, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"HARNESS: Tool call {i} arguments (raw): {tool_call.function.arguments}")

                # Prepare tool call details for conversation history
                tool_call_details = []
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        # Parse arguments safely
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            arguments = {"error": "Invalid JSON in arguments"}

                        tool_call_details.append(
                            {
                                "tool_call_id": tool_call.id,
                                "function_name": tool_call.function.name,
                                "arguments": arguments,
                            }
                        )

                conversation_history.append(
                    {
                        "iteration": iterations,
                        "message": message.content,
                        "tool_calls_requested": tool_call_details,
                        "tool_results": [],
                    }
                )

                # Check if there are tool calls to execute
                if message.tool_calls:
                    tool_results = []
                    print(f"HARNESS: Processing {len(message.tool_calls)} tool calls")

                    for i, tool_call in enumerate(message.tool_calls):
                        print(f"HARNESS: Tool call {i}: {tool_call.function.name}")

                        # Enhanced logging for edit operations
                        if tool_call.function.name == "edit_file":
                            args = json.loads(tool_call.function.arguments)
                            print(f"HARNESS: Edit target: {args.get('target_file', 'N/A')}")
                            print(f"HARNESS: Edit instructions: {args.get('instructions', 'N/A')}")
                            if 'line_edits' in args:
                                print(f"HARNESS: Line edits count: {len(args['line_edits'])}")
                                for j, edit in enumerate(args['line_edits'][:3]):  # Show first 3 edits
                                    edit_type = edit.get('type', 'unknown')
                                    line_num = edit.get('line_number', 'N/A')
                                    print(f"HARNESS: Edit {j}: {edit_type} at line {line_num}")

                        result = self._execute_tool_call(tool_call)
                        print(f"HARNESS: Tool {i} result success: {result.get('success', 'N/A')}")

                        if result.get('success') and result.get('content'):
                            content = str(result['content'])
                            print(f"HARNESS: Tool {i} content: {content}")

                        # Error reporting
                        if 'error' in result:
                            print(f"HARNESS: Tool {i} error: {result['error']}")
                            if result.get('syntax_error'):
                                print(f"HARNESS: SYNTAX ERROR at line {result.get('syntax_line', 'N/A')}: {result.get('syntax_msg', 'N/A')}")
                                if 'attempted_changes' in result:
                                    print(f"HARNESS: Attempted changes: {result['attempted_changes']}")
                        elif result.get('success') and 'changes_made' in result:
                            print(f"HARNESS: Changes applied: {result['changes_made'][:3]}")  # Show first 3 changes
                            if tool_call.function.name == "edit_file":
                                made_code_changes = True

                        tool_results.append(
                            {
                                "tool_call_id": tool_call.id,
                                "function_name": tool_call.function.name,
                                "result": result,
                            }
                        )

                        # Add tool result to messages
                        messages.append(
                            {
                                "role": "tool",
                                "content": json.dumps(result),
                                "tool_call_id": tool_call.id,
                            }
                        )

                    conversation_history[-1]["tool_results"] = tool_results
                else:
                    # No tool calls from the model. Enforce completion guard.
                    if not made_code_changes and iterations < max_iterations:
                        print(f"HARNESS: No tool calls yet and no edits made. Prompting agent to implement a change before completion.")
                        messages.append({
                            "role": "system",
                            "content": (
                                "Stop exploring and implement now: open the confirmed file, apply a minimal edit_file "
                                "to the target function, read it back, and continue with small iterative edits until "
                                "the change aligns with the expected behavior/diff."
                            ),
                        })
                        continue
                    # Either edits were made or we hit max iterations; allow completion
                    print(f"HARNESS: No tool calls, task complete at iteration {iterations}")
                    break

            except Exception as e:
                print(f"HARNESS: EXCEPTION CAUGHT IN ITERATION {iterations}: {type(e).__name__}: {str(e)}")
                tb_string = traceback.format_exc()
                sanitized_tb = sanitize_traceback(tb_string)
                print(f"HARNESS: Traceback:\n{sanitized_tb}")
                return {
                    "success": False,
                    "error": f"Error during execution at iteration {iterations}: {type(e).__name__}: {str(e)}",
                    "iterations": iterations,
                    "conversation_history": conversation_history,
                    "made_code_changes": made_code_changes,
                }

        return {
            "success": made_code_changes,
            "final_response": messages[-1]["content"] if messages else "No response",
            "iterations": iterations,
            "conversation_history": conversation_history,
            "max_iterations_reached": iterations >= max_iterations,
            "made_code_changes": made_code_changes,
            "error": None if made_code_changes else "Run completed without any successful edits",
        }


def test_agent_harness():
    """Test the LiteLLM Agent Harness with a simple task"""
    print("\n=== Testing LiteLLM Agent Harness ===")

    # Create a test harness (without container for local testing)
    harness = LiteLLMAgentHarness(
        model_name="claude-3-haiku-20240307",
        container=None,
        base_path="./test_workspace",
    )

    # Simple test task
    task_prompt = """
Create a simple Python script called 'hello.py' that:
1. Defines a function called greet(name) that returns a greeting message
2. Has a main section that calls greet("World") and prints the result
3. Make sure the file is properly formatted
    """

    print(f"Task: {task_prompt}")
    print("\nExecuting task...")

    result = harness.execute_task(task_prompt, max_iterations=5)

    print(f"\nTask completed. Success: {result['success']}")
    print(f"Iterations used: {result['iterations']}")

    if result["success"]:
        print(f"Final response: {result['final_response']}")
        print(f"\nFull Conversation History ({len(result['conversation_history'])} steps):")
        for i, step in enumerate(result["conversation_history"], 1):
            print(f"\n=== STEP {i} ===")
            print(f"Message: {step.get('message', 'No message')}")

            if step.get("tool_calls_requested"):
                print(f"Tool calls requested ({len(step['tool_calls_requested'])}):")
                for j, tool_call in enumerate(step["tool_calls_requested"], 1):
                    print(f"  {j}. {tool_call['function_name']}")
                    print(f"     Arguments: {json.dumps(tool_call.get('arguments', {}), indent=6)}")

            if step.get("tool_results"):
                print(f"Tool results ({len(step['tool_results'])}):")
                for j, result in enumerate(step["tool_results"], 1):
                    print(f"  {j}. {result.get('function_name', 'unknown')}")
                    print(f"     Success: {result.get('result', {}).get('success', 'unknown')}")
                    if result.get('result', {}).get('content'):
                        # Show full content without truncation
                        content = str(result['result']['content'])
                        print(f"     Content: {content}")
                    if result.get('result', {}).get('error'):
                        print(f"     Error: {result['result']['error']}")
    else:
        print(f"Error: {result['error']}")

    return result
