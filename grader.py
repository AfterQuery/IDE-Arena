import re
import difflib
from pathlib import Path

from constants import TestStatus
from docker_utils import run_command_in_container
from diff_verifier import DiffVerifier

def extract_final_agent_code(container) -> dict:
    print("GRADER: Extracting final agent code state...")

    search_patterns = [
        ("*.py", "Python files"),
        ("*.js", "JavaScript files"),
        ("*.ts", "TypeScript files"),
        ("*.jsx", "React files"),
        ("*.tsx", "TypeScript React files"),
        ("*.java", "Java files"),
        ("*.cpp", "C++ files"),
        ("*.c", "C files"),
        ("*.go", "Go files"),
        ("*.rs", "Rust files"),
        ("*.rb", "Ruby files"),
        ("*.php", "PHP files")
    ]

    final_code_state = {}

    for pattern, description in search_patterns:
        find_result = run_command_in_container(
            container=container,
            command=[
                "find", "/app", "-type", "f",
                "-not", "-path", "*/node_modules/*",
                "-not", "-path", "*/__pycache__/*",
                "-not", "-path", "*/.venv/*",
                "-not", "-path", "*/venv/*",
                "-not", "-path", "*/dist/*",
                "-not", "-path", "*/build/*",
                "-not", "-path", "*/target/*",
                "-not", "-path", "*/vendor/*",
                "-not", "-path", "*/.git/*",
                "-name", pattern
            ],
            stream=False,
        )

        if find_result.get('exit_code') == 0:
            found_files = [f.strip() for f in find_result.get('output', '').split('\n') if f.strip()]

            for file_path in found_files:
                cat_result = run_command_in_container(
                    container=container,
                    command=["cat", file_path],
                    stream=False,
                )

                if cat_result.get('exit_code') == 0:
                    relative_path = file_path.replace('/app/', '') if file_path.startswith('/app/') else file_path
                    final_code_state[relative_path] = cat_result.get('output', '')

    return final_code_state

def extract_lab_quality_metrics(agent_execution_data: dict | None) -> dict:

    if not agent_execution_data:
        return {
            "agent_success": False,
            "made_code_changes": False,
            "has_syntax_errors": True,  # Conservative assumption
            "total_iterations": 0,
            "conversation_trace": [],
            "final_agent_response": ""
        }

    agent_success = agent_execution_data.get("success", False)
    made_code_changes = agent_execution_data.get("made_code_changes", False)
    conversation_history = agent_execution_data.get("conversation_history", [])
    final_response = agent_execution_data.get("final_response", "")

    has_syntax_errors = False
    successful_code_changes = 0

    for conversation_turn in conversation_history:
        tool_results = conversation_turn.get("tool_results", [])
        for tool_result in tool_results:
            if tool_result.get("function_name") == "edit_file":
                result_data = tool_result.get("result", {})
                if result_data.get("success", False):
                    successful_code_changes += 1
                else:
                    error_msg = result_data.get("error", "").lower()
                    if any(keyword in error_msg for keyword in
                          ["syntax error", "syntaxerror", "indentation", "unexpected indent",
                           "invalid syntax", "unterminated", "unindent", "expected an indented"]):
                        has_syntax_errors = True

    actual_made_changes = successful_code_changes > 0

    print(f"GRADER: Lab quality metrics - Agent Success: {agent_success}")
    print(f"GRADER: Harness reported changes: {made_code_changes}, Actual detected changes: {actual_made_changes}")
    print(f"GRADER: Successful edits: {successful_code_changes}, Has Syntax Errors: {has_syntax_errors}")

    return {
        "agent_success": agent_success,
        "made_code_changes": actual_made_changes,  # Use actual detection instead of harness flag
        "has_syntax_errors": has_syntax_errors,
        "total_iterations": len(conversation_history),
        "conversation_trace": conversation_history,  # Full trace for labs
        "final_agent_response": final_response,
        "successful_edits": successful_code_changes,  # Additional metric for labs
    }

def run_grading_in_container(container, task_id: str, test_type: str = None, dataset_dir: str | None = None,
                          agent_execution_data: dict | None = None) -> dict:

    print(f"GRADER: Running tests with task_id: '{task_id}'")
    print(f"GRADER: Command: ['./run_tests.sh', '{task_id}']")

    lab_metrics = extract_lab_quality_metrics(agent_execution_data)
    print(f"GRADER: Lab training metrics extracted: {lab_metrics}")

    debug_result = run_command_in_container(
        container=container,
        command=[
            "find", "/app", "-type", "f", "-name", "*.py",
            "-not", "-path", "*/node_modules/*",
            "-not", "-path", "*/__pycache__/*",
            "-not", "-path", "*/.venv/*",
            "-not", "-path", "*/venv/*",
            "-not", "-path", "*/dist/*",
            "-not", "-path", "*/build/*",
            "-not", "-path", "*/target/*",
            "-not", "-path", "*/vendor/*",
            "-not", "-path", "*/.git/*",
        ],
        stream=False,
    )
    print(f"GRADER: Python files in container:")
    print(debug_result.get('output', 'No output'))

    structure_result = run_command_in_container(
        container=container,
        command=["ls", "-la", "/app/"],
        stream=False,
    )
    print(f"GRADER: Container /app structure:")
    print(structure_result.get('output', 'No output'))

    result = run_command_in_container(
        container=container,
        command=["./run_tests.sh", task_id],
        stream=False,
    )

    print(f"GRADER: Test command exit code: {result.get('exit_code')}")
    print(f"GRADER: Test output length: {len(result.get('output', ''))}")
    print(f"GRADER: Full test output:")
    print("=" * 80)
    print(result.get('output', ''))
    print("=" * 80)

    # SWE-bench style diff comparison (primary verification method)
    diff_results = None
    try:
        if dataset_dir:
            task_dir = Path(dataset_dir) / "tasks" / task_id
        if task_dir.exists():
            golden_diff_path = task_dir / "task_diff.txt"
            if golden_diff_path.exists():
                golden_diff = golden_diff_path.read_text(encoding='utf-8')

                agent_diff = ""

                git_diff_result = run_command_in_container(
                    container=container,
                    command=["git", "-C", "/app", "diff", "HEAD"],
                    stream=False,
                )
                if git_diff_result.get('exit_code') == 0:
                    agent_diff = git_diff_result.get('output', '')

                if not agent_diff.strip():
                    git_add_result = run_command_in_container(
                        container=container,
                        command=["git", "-C", "/app", "add", "-A"],
                        stream=False,
                    )
                    if git_add_result.get('exit_code') == 0:
                        staged_diff_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "diff", "--cached"],
                            stream=False,
                        )
                        if staged_diff_result.get('exit_code') == 0:
                            agent_diff = staged_diff_result.get('output', '')

                if not agent_diff.strip():
                    commit_result = run_command_in_container(
                        container=container,
                        command=["git", "-C", "/app", "commit", "-m", "agent changes snapshot", "--allow-empty"],
                        stream=False,
                    )
                    if commit_result.get('exit_code') == 0:
                        show_diff_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "diff", "HEAD~1", "HEAD"],
                            stream=False,
                        )
                        if show_diff_result.get('exit_code') == 0:
                            agent_diff = show_diff_result.get('output', '')

                # File-by-file fallback if all git methods fail
                if not agent_diff.strip():
                    search_patterns = [
                        ("/app", "*.py"), ("/app", "*.js"), ("/app", "*.ts"),
                        ("/app", "*.jsx"), ("/app", "*.tsx"), ("/app", "*.java"),
                        ("/app", "*.cpp"), ("/app", "*.c"), ("/app", "*.go")
                    ]

                    all_files = []
                    for search_dir, pattern in search_patterns:
                        find_result = run_command_in_container(
                            container=container,
                            command=[
                                "find", search_dir, "-type", "f",
                                "-not", "-path", "*/node_modules/*",
                                "-not", "-path", "*/__pycache__/*",
                                "-not", "-path", "*/.venv/*",
                                "-not", "-path", "*/venv/*",
                                "-not", "-path", "*/dist/*",
                                "-not", "-path", "*/build/*",
                                "-not", "-path", "*/target/*",
                                "-not", "-path", "*/vendor/*",
                                "-not", "-path", "*/.git/*",
                                "-name", pattern
                            ],
                            stream=False,
                        )
                        if find_result.get('exit_code') == 0:
                            found_files = [p for p in find_result.get('output', '').split('\n') if p.strip()]
                            all_files.extend(found_files)

                    all_files = list(set(all_files))

                    fallback_diffs = []

                    for abs_path in all_files:
                        try:
                            if abs_path.startswith('/app/'):
                                rel_path = abs_path[len('/app/'):]
                            else:
                                rel_path = abs_path

                            # Get baseline version
                            baseline = run_command_in_container(
                                container=container,
                                command=["git", "-C", "/app", "show", f"HEAD:{rel_path}"],
                                stream=False,
                            )

                            baseline_content = ""
                            if baseline.get('exit_code') == 0:
                                baseline_content = baseline.get('output', '')
                            else:
                                # If no baseline available, skip this file
                                continue

                            # Get current version
                            current = run_command_in_container(
                                container=container,
                                command=["cat", abs_path],
                                stream=False,
                            )
                            if current.get('exit_code') != 0:
                                continue

                            current_content = current.get('output', '')

                            if baseline_content == current_content:
                                continue  # No changes

                            # Generate diff for changed files
                            a_lines = baseline_content.splitlines(keepends=True)
                            b_lines = current_content.splitlines(keepends=True)
                            udiff = difflib.unified_diff(
                                a_lines, b_lines, fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}"
                            )
                            diff_text = ''.join(udiff)
                            if diff_text.strip():
                                fallback_diffs.append(diff_text)

                        except Exception:
                            continue

                    if fallback_diffs:
                        agent_diff = '\n'.join(fallback_diffs)

                if agent_diff:
                    agent_diff = _filter_diff_for_source_files(agent_diff)

                # Extract final agent code for labs
                final_code_state = extract_final_agent_code(container)

                agent_made_changes = len(agent_diff.strip()) > 0

                diff_results = {
                    "method": "lab_training_binary",
                    "agent_made_changes": agent_made_changes,
                    "agent_diff": agent_diff,
                    "golden_diff": golden_diff,
                    "final_code_state": final_code_state,
                    "lab_training_metrics": lab_metrics,
                }

            else:
                print(f"GRADER: No task_diff.txt found for task {task_id}")
    except Exception as e:
        print(f"GRADER: Error running diff comparison: {e}")

    individual_test_results = parse_test_output(result.get('output', ''), test_type)

    num_passed = sum(1 for status in individual_test_results.values() if status == TestStatus.PASSED)
    num_failed = sum(1 for status in individual_test_results.values() if status == TestStatus.FAILED)
    total_tests = len(individual_test_results) if individual_test_results else 1

    print(f"GRADER: Parsed {total_tests} individual tests ({num_passed} passed, {num_failed} failed)")

    if diff_results:
        lab_training_metrics = diff_results.get('lab_training_metrics', {})

        task_success = (
            result.get("exit_code") == 0 and  # Tests passed
            lab_training_metrics.get("agent_success", False) and  # Agent completed successfully
            lab_training_metrics.get("made_code_changes", False) and  # Agent made changes
            not lab_training_metrics.get("has_syntax_errors", True)  # No syntax errors
        )

        print(f"GRADER: AI Lab Training Assessment - Raw Metrics")
        print(f"GRADER: Tests Passed: {result.get('exit_code') == 0}")
        print(f"GRADER: Agent Success: {lab_training_metrics.get('agent_success', False)}")
        print(f"GRADER: Made Changes: {lab_training_metrics.get('made_code_changes', False)}")
        print(f"GRADER: No Syntax Errors: {not lab_training_metrics.get('has_syntax_errors', True)}")

        test_status_map = individual_test_results if individual_test_results else {"lab_evaluation": TestStatus.PASSED if task_success else TestStatus.FAILED}

        if not individual_test_results:
            num_passed = 1 if task_success else 0
            num_failed = 0 if task_success else 1
            total_tests = 1

        verification_type = "lab_training"
    else:
        print(f"GRADER: Evaluation failed, no verification possible")
        test_status_map = individual_test_results if individual_test_results else {"verification_failed": TestStatus.FAILED}

        if not individual_test_results:
            num_passed = 0
            num_failed = 1
            total_tests = 1

        verification_type = "verification_failed"

    validation_warnings = []
    validation_errors = []

    if verification_type == "lab_training":
        print(f"GRADER: Using AI lab training validation criteria")

        if diff_results:
            lab_training_metrics = diff_results.get('lab_training_metrics', {})

            if task_success:
                validation_warnings.append("Task completed successfully - high quality training example")
                validation_warnings.append(f"Agent completed in {lab_training_metrics.get('total_iterations', 0)} iterations")
            else:
                if not result.get("exit_code") == 0:
                    validation_errors.append("Tests failed - functional requirements not met")
                if not lab_training_metrics.get("agent_success", False):
                    validation_errors.append("Agent execution failed - incomplete implementation")
                if not lab_training_metrics.get("made_code_changes", False):
                    validation_errors.append("No code changes made - agent did not attempt implementation")
                if lab_training_metrics.get("has_syntax_errors", True):
                    validation_errors.append("Syntax errors detected - invalid code generated")

            final_code_state = diff_results.get('final_code_state', {})
            if final_code_state:
                validation_warnings.append(f"Final code state captured: {len(final_code_state)} files")
            else:
                validation_warnings.append("No final code state captured")
        else:
            validation_errors.append("Could not analyze agent execution - no training data available")

    else:
        validation_errors.append("Lab training evaluation failed - insufficient data")

    pass_rate = num_passed / total_tests if total_tests > 0 else 0.0

    if diff_results:
        lab_training_metrics = diff_results.get('lab_training_metrics', {})
        task_success_binary = (
            result.get("exit_code") == 0 and
            lab_training_metrics.get("agent_success", False) and
            lab_training_metrics.get("made_code_changes", False) and
            not lab_training_metrics.get("has_syntax_errors", True)
        )
        lab_training_outcome = 1.0 if task_success_binary else 0.0
    else:
        task_success_binary = False
        lab_training_outcome = 0.0

    grading_result = {
        "success": result["exit_code"] == 0,
        "exit_code": result["exit_code"],
        "raw_output": result["output"],
        "tests_passed": num_passed,
        "tests_failed": num_failed,
        "total_tests": total_tests,
        "test_details": test_status_map,
        "pass_rate": num_passed / total_tests if total_tests > 0 else 0,
        "validation_warnings": validation_warnings,
        "validation_errors": validation_errors,
        "meets_minimum_requirements": total_tests >= 6 and num_passed == total_tests,
        "lab_training_outcome": lab_training_outcome,  # Clean binary for AI labs
        "individual_test_results": individual_test_results,  # Detailed test-by-test results
    }

    grading_result["verification_type"] = verification_type

    if verification_type == "lab_training" and diff_results:
        grading_result.update({
            "lab_training_data": {
                "conversation_trace": diff_results.get('lab_training_metrics', {}).get('conversation_trace', []),
                "final_code_state": diff_results.get('final_code_state', {}),
                "agent_execution_success": diff_results.get('lab_training_metrics', {}).get('agent_success', False),
                "made_code_changes": diff_results.get('lab_training_metrics', {}).get('made_code_changes', False),
                "has_syntax_errors": diff_results.get('lab_training_metrics', {}).get('has_syntax_errors', True),
                "total_iterations": diff_results.get('lab_training_metrics', {}).get('total_iterations', 0),
                "final_agent_response": diff_results.get('lab_training_metrics', {}).get('final_agent_response', ''),
                "successful_edits": diff_results.get('lab_training_metrics', {}).get('successful_edits', 0),
                "individual_tests_passed": num_passed,
                "individual_tests_failed": num_failed,
                "individual_tests_total": total_tests,
                "individual_test_pass_rate": pass_rate,
            },
            "binary_outcome": lab_training_outcome,
            "task_success": task_success_binary,
            "task_success_binary": task_success_binary,  # Explicit binary flag for training
        })
        print(f"GRADER: Added AI lab training data")
    else:
        grading_result.update({
            "lab_training_data": None,
            "binary_outcome": 0.0,
            "task_success": False,
            "task_success_binary": False,
        })

    return grading_result

def _filter_diff_for_source_files(diff_content: str) -> str:

    if not diff_content:
        return diff_content

    try:
        lines = diff_content.split('\n')
        filtered_lines = []
        current_file = None
        in_irrelevant_file = False

        # Patterns for files to exclude from diff
        exclude_patterns = [
            'node_modules/',
            '.package-lock.json',
            'package-lock.json',
            'package.json',
            'yarn.lock',
            '.npm/',
            '.yarn/',
            '__pycache__/',
            '.pytest_cache/',
            'coverage/',
            '.coverage',
            '.nyc_output/',
            'build/',
            'dist/',
            '.DS_Store',
            'Thumbs.db',
            '*.log',
            '*.tmp',
            'tmp/',
            'temp/',
            '.git/',
            '.vscode/',
            '.idea/',
        ]

        for line in lines:
            if line.startswith('diff --git'):
                # Extract file path
                parts = line.split()
                if len(parts) >= 4:
                    file_path = parts[3][2:]  # Remove 'b/' prefix
                    current_file = file_path

                    in_irrelevant_file = any(pattern in file_path or file_path.endswith(pattern.replace('*', ''))
                                           for pattern in exclude_patterns)

                    if not in_irrelevant_file:
                        print(f"GRADER: Including file in diff: {file_path}")
                        filtered_lines.append(line)
                    else:
                        print(f"GRADER: Excluding irrelevant file from diff: {file_path}")
                else:
                    filtered_lines.append(line)
            elif not in_irrelevant_file:
                filtered_lines.append(line)

        filtered_diff = '\n'.join(filtered_lines)
        print(f"GRADER: Filtered diff from {len(lines)} to {len(filtered_lines)} lines")
        return filtered_diff

    except Exception as e:
        print(f"GRADER: Error filtering diff: {e}")
        return diff_content  # Return original if filtering fails

def _reconstruct_original_from_diff(golden_diff: str, current_content: str) -> str:

    try:
        import re

        # Parse the golden diff to understand what changes were made
        # The golden diff shows the changes needed to transform original -> expected

        lines = golden_diff.split('\n')
        original_lines = []
        in_file_section = False
        file_path = None

        for line in lines:
            if line.startswith('diff --git'):
                # Extract file path
                parts = line.split()
                if len(parts) >= 4:
                    file_path = parts[3][2:]  # Remove 'b/' prefix

            elif line.startswith('@@'):
                in_file_section = True
                continue

            elif in_file_section:
                if line.startswith('-') and not line.startswith('---'):
                    original_lines.append(line[1:])  # Remove the '-' prefix
                elif line.startswith('+') and not line.startswith('+++'):
                    continue
                elif line.startswith(' '):
                    original_lines.append(line[1:])  # Remove the ' ' prefix
                elif not line.strip():
                    original_lines.append('')

        if original_lines:
            reconstructed = '\n'.join(original_lines)
            print(f"GRADER: Reconstructed {len(original_lines)} lines from golden diff")
            return reconstructed
        else:
            print(f"GRADER: Could not reconstruct original from golden diff")
            return ""

    except Exception as e:
        print(f"GRADER: Error reconstructing original from diff: {e}")
        return ""

def detect_test_framework(output: str) -> str:

    # Check for framework-specific signatures in order of specificity
    patterns = {
        # Python test frameworks
        "pytest": [
            r"===.*pytest",
            r"collected \d+ items?",
            r"platform .* -- Python",
            r"PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS"
        ],
        "unittest": [
            r"Ran \d+ tests? in \d+\.\d+s",
            r"FAIL:|ERROR:|OK",
            r"----------------------------------------------------------------------"
        ],

        # JavaScript/TypeScript frameworks
        "jest": [
            r"PASS |FAIL ",
            r"Test Suites:",
            r"Tests:",
            r"Snapshots:",
            r"✓|✕|×|✗"
        ],
        "mocha": [
            r"^\s*✓",
            r"^\s*\d+\) ",
            r"\d+ passing",
            r"\d+ failing"
        ],
        "jasmine": [
            r"Started.*Jasmine",
            r"Spec.*|Suite.*",
            r"\d+ specs?, \d+ failures?"
        ],

        # Java frameworks
        "maven": [
            r"BUILD SUCCESS|BUILD FAILURE",
            r"\[INFO\].*T E S T S",
            r"Tests run: \d+, Failures: \d+"
        ],
        "junit": [
            r"JUnit.*version",
            r"Time: \d+\.\d+",
            r"Tests run: \d+.*Failures: \d+"
        ],
        "gradle": [
            r"BUILD SUCCESSFUL|BUILD FAILED",
            r"> Task :test"
        ],

        # Go
        "go": [
            r"=== RUN",
            r"--- PASS:|--- FAIL:",
            r"PASS\n.*coverage:",
            r"ok\s+.*\s+\d+\.\d+s"
        ],

        # Rust
        "cargo": [
            r"running \d+ tests?",
            r"test .* \.\.\. ok|FAILED",
            r"test result:"
        ],

        # Ruby
        "rspec": [
            r"RSpec",
            r"\d+ examples?, \d+ failures?",
            r"Finished in \d+\.\d+ seconds"
        ],
        "minitest": [
            r"# Running:",
            r"\d+ runs?, \d+ assertions?",
            r"Finished in \d+\.\d+s"
        ],

        # PHP
        "phpunit": [
            r"PHPUnit \d+\.\d+",
            r"^\.+F*E*S*$",
            r"Tests: \d+, Assertions: \d+"
        ],

        # .NET
        "dotnet": [
            r"Test run for.*\.dll",
            r"Passed.*Failed.*Skipped.*Total",
            r"Total tests: \d+"
        ]
    }

    scores = {}
    for framework, framework_patterns in patterns.items():
        score = 0
        for pattern in framework_patterns:
            if re.search(pattern, output, re.MULTILINE | re.IGNORECASE):
                score += 1
        if score > 0:
            scores[framework] = score

    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]

    return None

def parse_test_output_universal(output: str) -> dict:

    test_status_map = {}

    # Common patterns across test frameworks
    # Format: (pattern, status, test_name_group)
    test_patterns = [
        # General pass/fail patterns
        (r"^✓\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.PASSED, 1),  # ✓ test name (time)
        (r"^✔\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.PASSED, 1),  # ✔ test name
        (r"^√\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.PASSED, 1),  # √ test name
        (r"^✕\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.FAILED, 1),  # ✕ test name
        (r"^✖\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.FAILED, 1),  # ✖ test name
        (r"^×\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.FAILED, 1),  # × test name
        (r"^✗\s+(.+?)(?:\s+\(\d+(?:\.\d+)?m?s\))?$", TestStatus.FAILED, 1),  # ✗ test name

        # OK/FAIL patterns
        (r"^ok\s+\d+\s+-\s+(.+)$", TestStatus.PASSED, 1),  # ok 1 - test name (TAP)
        (r"^not ok\s+\d+\s+-\s+(.+)$", TestStatus.FAILED, 1),  # not ok 1 - test name (TAP)
        (r"^ok\s+(.+?)(?:\s+\d+(?:\.\d+)?m?s)?$", TestStatus.PASSED, 1),  # ok test.name
        (r"^FAIL\s+(.+?)(?:\s+\[\d+(?:\.\d+)?m?s\])?$", TestStatus.FAILED, 1),  # FAIL test.name
        (r"^PASS\s+(.+?)(?:\s+\[\d+(?:\.\d+)?m?s\])?$", TestStatus.PASSED, 1),  # PASS test.name

        # Verbose patterns
        (r"^(?:PASSED|passed)\s+(?:::)?\s*(.+?)(?:\s+\[.*\])?$", TestStatus.PASSED, 1),
        (r"^(?:FAILED|failed)\s+(?:::)?\s*(.+?)(?:\s+\[.*\])?$", TestStatus.FAILED, 1),
        (r"^(?:ERROR|error)\s+(?:::)?\s*(.+?)(?:\s+\[.*\])?$", TestStatus.FAILED, 1),
        (r"^(?:SKIPPED|skipped)\s+(?:::)?\s*(.+?)(?:\s+\[.*\])?$", TestStatus.FAILED, 1),

        # Numbered test patterns
        (r"^\s*\d+\)\s+(.+?)\s+\.{3,}\s+(PASSED|passed|OK|ok)$", TestStatus.PASSED, 1),
        (r"^\s*\d+\)\s+(.+?)\s+\.{3,}\s+(FAILED|failed|FAIL|fail)$", TestStatus.FAILED, 1),

        # Test method patterns
        (r"^test[A-Z]\w*.*\.{3,}\s*(ok|OK|passed|PASSED)$", TestStatus.PASSED, 0),
        (r"^test[A-Z]\w*.*\.{3,}\s*(fail|FAIL|failed|FAILED)$", TestStatus.FAILED, 0),

        # Go test patterns
        (r"^--- PASS:\s+(.+?)\s+\([\d.]+s\)$", TestStatus.PASSED, 1),
        (r"^--- FAIL:\s+(.+?)\s+\([\d.]+s\)$", TestStatus.FAILED, 1),
        (r"^=== RUN\s+(.+)$", None, 1),  # Track but don't assign status yet

        # Rust test patterns
        (r"^test\s+(.+?)\s+\.\.\.\s+ok$", TestStatus.PASSED, 1),
        (r"^test\s+(.+?)\s+\.\.\.\s+FAILED$", TestStatus.FAILED, 1),

        # Ruby RSpec patterns
        (r"^\s*✓\s+(.+)$", TestStatus.PASSED, 1),
        (r"^\s*✗\s+(.+)$", TestStatus.FAILED, 1),
        (r"^\s*\.\s*$", TestStatus.PASSED, 0),  # Single dot = pass
        (r"^\s*F\s*$", TestStatus.FAILED, 0),  # F = failure

        # .NET patterns
        (r"^\s*Passed\s+(.+)$", TestStatus.PASSED, 1),
        (r"^\s*Failed\s+(.+)$", TestStatus.FAILED, 1),
    ]

    running_tests = set()
    test_counter = 0

    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue

        for pattern, status, name_group in test_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                if status is None:
                    if name_group == 0:
                        test_name = match.group(0)
                    else:
                        test_name = match.group(name_group)
                    running_tests.add(test_name.strip())
                else:
                    # Extract test name
                    if name_group == 0:
                        test_name = f"test_{test_counter}"
                        test_counter += 1
                    else:
                        test_name = match.group(name_group)

                    test_name = test_name.strip()

                    test_name = re.sub(r'\s+\[\d+(?:\.\d+)?m?s\]$', '', test_name)
                    test_name = re.sub(r'\s+\(\d+(?:\.\d+)?m?s\)$', '', test_name)
                    test_name = re.sub(r'^(test_)?', '', test_name)

                    if test_name and not test_name.startswith('='):
                        test_status_map[test_name] = status
                        running_tests.discard(test_name)
                break

    if not test_status_map:
        summary_patterns = [
            (r"Tests?:\s*(\d+)\s+passed", r"Tests?:\s*(\d+)\s+failed"),
            (r"(\d+)\s+pass(?:ed|ing)", r"(\d+)\s+fail(?:ed|ing|ures?)"),
            (r"(\d+)\s+tests?\s+pass(?:ed)?", r"(\d+)\s+tests?\s+fail(?:ed)?"),
            (r"All\s+(?:\d+\s+)?tests?\s+pass(?:ed)?", r"(\d+)\s+tests?\s+fail(?:ed)?"),
        ]

        for pass_pattern, fail_pattern in summary_patterns:
            passed = 0
            failed = 0

            pass_match = re.search(pass_pattern, output, re.IGNORECASE)
            if pass_match:
                try:
                    if pass_match.groups():
                        passed = int(pass_match.group(1))
                    elif "all" in pass_match.group(0).lower():
                        # Extract number from "All X tests passed"
                        num_match = re.search(r"(\d+)", pass_match.group(0))
                        passed = int(num_match.group(1)) if num_match else 1
                    else:
                        passed = 1
                except (ValueError, IndexError):
                    passed = 1

            fail_match = re.search(fail_pattern, output, re.IGNORECASE)
            if fail_match and fail_match.groups():
                try:
                    failed = int(fail_match.group(1))
                except (ValueError, IndexError):
                    failed = 0

            if passed > 0 or failed > 0:
                for i in range(passed):
                    test_status_map[f"test_passed_{i+1}"] = TestStatus.PASSED
                for i in range(failed):
                    test_status_map[f"test_failed_{i+1}"] = TestStatus.FAILED
                break

    # Final fallback: check overall success/failure indicators
    if not test_status_map:
        success_indicators = [
            r"all tests pass",
            r"test.*success",
            r"build success",
            r"tests? pass",
            r"0 fail",
            r"no fail",
            r"100%.*pass"
        ]

        failure_indicators = [
            r"test.*fail",
            r"build fail",
            r"error",
            r"assertion.*fail",
            r"expected.*but got",
            r"test.*broken"
        ]

        has_success = any(re.search(pattern, output, re.IGNORECASE) for pattern in success_indicators)
        has_failure = any(re.search(pattern, output, re.IGNORECASE) for pattern in failure_indicators)

        if has_failure:
            test_status_map["test_suite"] = TestStatus.FAILED
        elif has_success:
            test_status_map["test_suite"] = TestStatus.PASSED
        elif "test" in output.lower():
            test_status_map["test_suite"] = TestStatus.FAILED

    return test_status_map

def parse_test_output(output: str, test_type: str = None) -> dict:

    if not test_type:
        test_type = detect_test_framework(output)
        print(f"GRADER: Auto-detected test framework: {test_type or 'unknown'}")

    # Try framework-specific parsers first if we know the type
    if test_type == "pytest":
        results = parse_log_pytest(output)
        if results:
            return results
    elif test_type == "maven":
        results = parse_log_maven(output)
        if results:
            return results
    elif test_type == "jest":
        results = parse_log_jest(output)
        if results:
            return results

    print(f"GRADER: Using universal test parser")
    return parse_test_output_universal(output)

def parse_log_pytest(log: str) -> dict[str, TestStatus]:

    test_status_map = {}

    status_first_regex = re.compile(r"^(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\s+([^\s]+)")
    status_last_regex = re.compile(r"^([^\s]+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)")

    for line in log.split("\n"):
        line = line.strip()

        match = status_first_regex.match(line)
        if match:
            status_str = match.group(1)
            test_name = match.group(2)
            _add_test_result(test_status_map, test_name, status_str)
            continue

        match = status_last_regex.match(line)
        if match:
            test_name = match.group(1)
            status_str = match.group(2)
            _add_test_result(test_status_map, test_name, status_str)
            continue

        if line.startswith("PASSED "):
            test_name = line[7:].split()[0] if len(line) > 7 else ""
            if test_name:
                _add_test_result(test_status_map, test_name, "PASSED")

        elif line.startswith("FAILED "):
            rest = line[7:]
            test_name = rest.split()[0] if rest else ""
            if test_name:
                _add_test_result(test_status_map, test_name, "FAILED")

        elif line.startswith("ERROR "):
            test_name = line[6:].split()[0] if len(line) > 6 else ""
            if test_name:
                 _add_test_result(test_status_map, test_name, "ERROR")

    if not test_status_map or len(test_status_map) == 0:
        summary_section = False
        for line in log.split("\n"):
            if "short test summary info" in line:
                summary_section = True
                continue

            if summary_section:
                if line.startswith("====="):
                    summary_section = False
                    break

                match = status_first_regex.match(line.strip())
                if match:
                    status_str = match.group(1)
                    test_name = match.group(2)
                    _add_test_result(test_status_map, test_name, status_str)

    return test_status_map

def _add_test_result(test_status_map, test_name, status_str):
    if test_name.startswith("=") or test_name.startswith("_"):
        return

    if " - " in test_name:
        test_name = test_name.split(" - ")[0]

    status = TestStatus.FAILED
    if status_str in ["PASSED", "XPASS"]:
        status = TestStatus.PASSED
    elif status_str == "SKIPPED":
        status = TestStatus.FAILED
    elif status_str == "XFAIL":
        status = TestStatus.PASSED

    test_status_map[test_name] = status

def parse_log_maven(log: str) -> dict[str, str]:

    test_status_map = {}
    current_test_name = "---NO TEST NAME FOUND YET---"

    test_name_pattern = r"^.*-Dtest=(\S+).*$"
    result_pattern = r"^.*BUILD (SUCCESS|FAILURE)$"

    for line in log.split("\n"):
        test_name_match = re.match(test_name_pattern, line.strip())
        if test_name_match:
            current_test_name = test_name_match.groups()[0]

        result_match = re.match(result_pattern, line.strip())
        if result_match:
            status = result_match.groups()[0]
            if status == "SUCCESS":
                test_status_map[current_test_name] = TestStatus.PASSED
            elif status == "FAILURE":
                test_status_map[current_test_name] = TestStatus.FAILED

    return test_status_map

def parse_log_jest(log: str) -> dict[str, TestStatus]:

    test_status_map = {}

    # Jest patterns to look for
    patterns = {
        TestStatus.PASSED: [r"✓\s+(.+)", r"PASS\s+(.+)", r"√\s+(.+)"],
        TestStatus.FAILED: [r"✕\s+(.+)", r"FAIL\s+(.+)", r"×\s+(.+)", r"✗\s+(.+)"]
    }

    lines = log.split('\n')
    current_test_file = None

    for line in lines:
        line = line.strip()

        if 'PASS' in line or 'FAIL' in line:
            # Extract test file name
            if line.startswith('PASS') or line.startswith('FAIL'):
                parts = line.split()
                if len(parts) > 1:
                    current_test_file = parts[1].split('/')[-1]

        for status, regex_patterns in patterns.items():
            for pattern in regex_patterns:
                import re
                match = re.search(pattern, line)
                if match:
                    test_name = match.group(1).strip()
                    full_test_name = f"{current_test_file}::{test_name}" if current_test_file else test_name
                    test_status_map[full_test_name] = status
                    break

    if not test_status_map:
        if "Tests:" in log and "passed" in log:
            import re
            match = re.search(r"Tests:\s+(\d+)\s+passed.*?(\d+)\s+total", log)
            if match:
                passed = int(match.group(1))
                total = int(match.group(2))
                failed = total - passed

                for i in range(passed):
                    test_status_map[f"test_{i+1}"] = TestStatus.PASSED
                for i in range(failed):
                    test_status_map[f"test_{passed+i+1}"] = TestStatus.FAILED

        # Fallback: if we see any test indicators but can't parse individual tests
        elif any(keyword in log.lower() for keyword in ["test", "spec", "pass", "fail"]):
            if "fail" in log.lower() or "error" in log.lower():
                test_status_map["integration_test"] = TestStatus.FAILED
            else:
                test_status_map["integration_test"] = TestStatus.PASSED

    return test_status_map

