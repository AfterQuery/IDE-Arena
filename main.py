#!/usr/bin/env python3
"""
Main CLI for Agent IDE Environment

Allows testing different coding agents against datasets with various models.
"""

import csv
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional

import docker
import typer


def sanitize_traceback(tb_string: str) -> str:
    pattern = r'File "([^"]+)",'

    def replace_path(match):
        full_path = match.group(1)
        filename = os.path.basename(full_path)
        return f'File "{filename}",'

    return re.sub(pattern, replace_path, tb_string)
from agent_utils import deploy_agent_in_container
from constants import Model
from docker_utils import run_command_in_container
from grader import run_grading_in_container
from rich import print
from rich.console import Console
from rich.syntax import Syntax
from util import parse_task_description

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)

app = typer.Typer(help="IDE Arena")
console = Console()


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text to make logs readable"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


class OutputCapture:
    """Captures all terminal output for logging purposes"""

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.captured_output = StringIO()
        self.log_file = None

    def __enter__(self):
        self.log_file = open(self.log_file_path, "w", encoding="utf-8")

        class TeeWriter:
            def __init__(self, original, log_file, captured):
                self.original = original
                self.log_file = log_file
                self.captured = captured

            def write(self, text):
                self.original.write(text)
                clean_text = strip_ansi_codes(text)
                self.log_file.write(clean_text)
                self.captured.write(clean_text)
                self.log_file.flush()

            def flush(self):
                self.original.flush()
                self.log_file.flush()

        sys.stdout = TeeWriter(
            self.original_stdout, self.log_file, self.captured_output
        )
        sys.stderr = TeeWriter(
            self.original_stderr, self.log_file, self.captured_output
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        if self.log_file:
            self.log_file.close()

    def get_captured_output(self):
        return self.captured_output.getvalue()


def create_log_entry(
    dataset: str,
    agent: str,
    model: str,
    task_id: Optional[str],
    start_time: datetime,
    end_time: datetime,
    success: bool,
    log_file_path: str,
    tests_passed: int = 0,
    total_tests: int = 0,
    pass_at_k: int = 1,
    num_passed_attempts: Optional[int] = None,
) -> dict:
    """Create a log entry for the CSV summary"""
    duration_seconds = (end_time - start_time).total_seconds()
    entry = {
        "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": dataset,
        "agent": agent,
        "model": model,
        "task_id": task_id or "all",
        "duration_seconds": round(duration_seconds, 2),
        "duration_human": f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s",
        "success": success,
        "tests_passed": tests_passed,
        "total_tests": total_tests,
        "test_success_rate": f"{tests_passed}/{total_tests}" if total_tests > 0 else "0/0",
        "log_file": log_file_path,
    }

    # Add pass@k fields if k > 1
    if pass_at_k > 1:
        entry["pass_at_k"] = pass_at_k
        entry["num_passed_attempts"] = num_passed_attempts if num_passed_attempts is not None else (1 if success else 0)

    return entry


def write_csv_log(log_entry: dict):
    """Write log entry to CSV file"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    csv_file = logs_dir / "benchmark_runs.csv"
    file_exists = csv_file.exists()

    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=log_entry.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(log_entry)


class VerboseContext:
    """Context manager for verbose logging control"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.original_level = logger.level
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARNING)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.setLevel(self.original_level)

    def log(self, message: str, level: str = "info"):
        """Log a message if verbose is enabled"""
        if self.verbose:
            if level == "debug":
                logger.debug(message)
            elif level == "info":
                logger.info(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)


def vprint(verbose: bool, message: str, level: str = "info"):
    """Print only if verbose is enabled"""
    if verbose:
        if level == "error":
            print(f"[red]{message}[/red]")
        else:
            print(message)


def pretty_print_conversation(conversation_data: dict, verbose: bool):
    """Pretty print conversation history and agent result in verbose mode"""
    if not verbose:
        return

    console.print("\n[bold blue]═══ AGENT EXECUTION DETAILS ═══[/bold blue]")

    if conversation_data.get("success"):
        console.print("[green]Execution Status: Success[/green]")
        console.print(
            f"[cyan]Model Used: {conversation_data.get('model_used', 'Unknown')}[/cyan]"
        )
        console.print(
            f"[cyan]Iterations: {conversation_data.get('iterations', 'Unknown')}[/cyan]"
        )

        if conversation_data.get("agent_response"):
            console.print("\n[bold]Final Agent Response:[/bold]")
            console.print(
                f"[dim]{conversation_data['agent_response'][:500]}{'...' if len(conversation_data['agent_response']) > 500 else ''}[/dim]"
            )
    else:
        console.print("[red]Execution Status: Failed[/red]")
        if conversation_data.get("error"):
            console.print(f"[red]Error: {conversation_data['error']}[/red]")

    conversation_history = conversation_data.get("conversation_history", [])
    if conversation_history:
        console.print(
            f"\n[bold]Conversation History ({len(conversation_history)} steps):[/bold]"
        )

        json_str = json.dumps(conversation_history, indent=2, ensure_ascii=False)

        syntax = Syntax(
            json_str, "json", theme="monokai", line_numbers=True, word_wrap=True
        )
        console.print(syntax)
    else:
        console.print("\n[yellow]No conversation history available[/yellow]")

    console.print("\n[bold blue]═══ END AGENT DETAILS ═══[/bold blue]\n")


@app.command()
def list_models():
    """List all models that can be used for benchmarking"""
    for model in Model:
        print(model.value)


@app.command()
def bench(
    dataset: str = typer.Option(..., help="Dataset name to use"),
    agent: str = typer.Option(..., help="Agent type to run. Options: oracle, gladiator"),
    model_name: str = typer.Option(
        ..., "--model", help="Model name (oracle or actual model)"
    ),
    task_id: Optional[str] = typer.Option(
        None, "--task-id", help="Specific task ID to run (runs all if not specified)"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    max_iterations: int = typer.Option(35, "--max-iterations", help="Maximum number of agent iterations (default: 35)"),
    pass_at_k: int = typer.Option(1, "--pass-at", help="Number of independent runs for pass@k evaluation (default: 1 for pass@1)"),
):
    """Benchmark a model against a ide-arena dataset with pass@k support"""

    start_time = datetime.now()

    if pass_at_k < 1:
        print(f"Error: --pass-at must be at least 1 (got {pass_at_k})")
        raise typer.Exit(1)

    if pass_at_k > 1 and agent == "oracle":
        print(f"Warning: pass@k with oracle agent is deterministic")
        print(f"Continuing with pass@{pass_at_k}...")

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    def normalize_model_name(model: str) -> str:
        """Normalize model name for filenames"""

        providers = ['openai/', 'anthropic/', 'gemini/', 'google/',
                     'xai/', 'meta/', 'mistral/', 'cohere/',
                     'huggingface/', 'replicate/', 'together/',
                     'aws/', 'azure/', 'vertex/', 'ai21/', 'aleph/',
                     'databricks/', 'fireworks/', 'groq/', 'perplexity/']

        normalized = model
        for provider in providers:
            normalized = normalized.replace(provider, '')

        normalized = normalized.replace('/', '_')
        return normalized

    def normalize_task_name(task: str, dataset_name: str) -> str:
        """Extract task name from task_id or dataset"""
        if task:
            return task
        # If no specific task, return 'all-tasks'
        return "all-tasks"

    normalized_model = normalize_model_name(model_name)
    normalized_task = normalize_task_name(task_id, dataset)

    # Extract dataset name from path
    dataset_name = Path(dataset).name

    # Build log filename with dataset name included
    # Format: {model}_{dataset}_{task}_pass@{k}.log
    if pass_at_k > 1:
        if task_id:
            log_filename = f"{normalized_model}_{dataset_name}_{normalized_task}_pass@{pass_at_k}.log"
        else:
            log_filename = f"{normalized_model}_{dataset_name}_all-tasks_pass@{pass_at_k}.log"
    else:
        if task_id:
            log_filename = f"{normalized_model}_{dataset_name}_{normalized_task}.log"
        else:
            log_filename = f"{normalized_model}_{dataset_name}_all-tasks.log"
    log_file_path = logs_dir / log_filename

    overall_success = True
    total_tests_passed = 0
    total_tests_run = 0

    # Pass@k tracking: stores results for all tasks
    all_tasks_pass_at_k_results = []

    with OutputCapture(str(log_file_path)):
        print(
            f"Starting benchmark run at {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"Dataset: {dataset}, Agent: {agent}, Model: {model_name}")
        if pass_at_k > 1:
            print(f"Pass@{pass_at_k} Evaluation: Running {pass_at_k} independent attempts per task")
        if task_id:
            print(f"Task: {task_id}")
        else:
            print("Running all tasks")
        print(f"Logging to: {log_file_path}")
        print("-" * 60)

        try:
            if verbose:
                logging.basicConfig(level=logging.DEBUG, format="%(message)s")
            if agent == "oracle":
                if model_name != "oracle":
                    vprint(
                        verbose, "Model name must be oracle for oracle agent", "error"
                    )
                    raise typer.Exit(1)
            elif agent == "gladiator":
                if model_name == "oracle":
                    vprint(
                        verbose,
                        "Model name must be a real model for gladiator agent",
                        "error",
                    )

            potential_path = Path(dataset)
            if potential_path.exists():
                dataset_dir = potential_path
            else:
                dataset_dir = Path("datasets") / dataset

            if not dataset_dir.exists():
                vprint(
                    verbose, f"Dataset directory {dataset_dir} does not exist.", "error"
                )
                raise typer.Exit(1)

            vprint(verbose, f"Running bench on dataset {dataset}...")

            dockerfile = dataset_dir / "Dockerfile"
            filenames_to_check = [
                "compose.yaml",
                "docker-compose.yaml",
                "docker-compose.yml",
            ]
            compose_file = None
            for fname in filenames_to_check:
                potential_path = dataset_dir / fname
                if potential_path.exists():
                    compose_file = potential_path
                    break
            test_script = dataset_dir / "run_tests.sh"
            task_dir = dataset_dir / "tasks" / (task_id if task_id else "")

            if (
                not dockerfile.exists()
                or not (compose_file and compose_file.exists())
                or not test_script.exists()
                or not task_dir.exists()
            ):
                vprint(
                    True,
                    f"Dataset {dataset} is missing some required files. "
                    f"\n\tDockerfile Exists:\t{dockerfile.exists()}"
                    f"\n\tDocker Compose Exists:\t{compose_file and compose_file.exists()}"
                    f"\n\tTest Script Exists:\t{test_script.exists()}"
                    f"\n\tTask Dir Exists:\t{task_dir.exists()}",
                    "error",
                )
                raise typer.Exit(1)

            client = docker.from_env()

            task_ids = (
                [d.name for d in task_dir.iterdir() if d.is_dir()]
                if task_id is None
                else [task_id]
            )
            with VerboseContext(verbose) as vctx:
                for current_task_id in task_ids:
                    vctx.log(f"Running task {current_task_id}...")
                    try:
                        # Check for pre-built task image from validate-docker (Cloud Build)
                        # This is passed via TASK_IMAGE env var from the K8s job
                        pre_built_image = os.environ.get("TASK_IMAGE")
                        if pre_built_image:
                            vctx.log(f"Pulling pre-built task image: {pre_built_image}")
                            try:
                                image = client.images.pull(pre_built_image)
                                image_tag = pre_built_image
                                vctx.log(f"Successfully pulled pre-built image: {pre_built_image}")
                                # Note: Pre-built image doesn't include tasks - we'll copy them after container starts
                            except Exception as pull_err:
                                vctx.log(f"Failed to pull pre-built image: {pull_err}", "warning")
                                vctx.log("Falling back to local Docker build...", "warning")
                                pre_built_image = None  # Fall back to building

                        if not pre_built_image:
                            vctx.log("Building Docker image...")
                            ds_label = Path(dataset).name
                            safe_label = re.sub(r"[^a-z0-9_.-]", "-", ds_label.lower())
                            image_tag = f"{safe_label}_test_image"
                            image, build_logs = client.images.build(
                                path=str(dataset_dir), tag=image_tag
                            )
                            for chunk in build_logs:
                                if "stream" in chunk:
                                    vctx.log(chunk["stream"].strip(), "debug")

                        vctx.log("Running Docker container...")
                        env_vars = {}

                        if os.environ.get("ANTHROPIC_API_KEY"):
                            env_vars["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")

                        if os.environ.get("OPENAI_API_KEY"):
                            env_vars["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")

                        if os.environ.get("GOOGLE_API_KEY"):
                            env_vars["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY")

                        container = client.containers.run(
                            image.id,
                            detach=True,
                            entrypoint=["/bin/sh", "-c"],
                            command=["tail -f /dev/null"],
                            environment=env_vars,
                        )

                        try:
                            container.reload()
                            if container.status != "running":
                                container.start()
                                container.reload()
                        except Exception as e:
                            pass

                        # If using pre-built image, copy tasks folder into container
                        # (pre-built image only has base repo, not tasks)
                        if pre_built_image:
                            tasks_src = dataset_dir / "tasks"
                            if tasks_src.exists():
                                print(f"CONTAINER: Copying tasks from {tasks_src} into container...")
                                import subprocess
                                import tarfile
                                import io

                                # Create a tar archive of the tasks folder
                                tar_stream = io.BytesIO()
                                with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                                    tar.add(str(tasks_src), arcname='tasks')
                                tar_stream.seek(0)

                                # Copy tar archive into container at /app
                                container.put_archive('/app', tar_stream.getvalue())
                                print("CONTAINER: Tasks folder copied successfully")

                                # Verify tasks were copied
                                verify_result = run_command_in_container(
                                    container=container,
                                    command=["ls", "-la", "/app/tasks/"],
                                    stream=False,
                                )
                                if verify_result.get("exit_code") == 0:
                                    print(f"CONTAINER: Tasks directory contents: {verify_result.get('output', '').strip()[:200]}")
                                else:
                                    print(f"CONTAINER: WARNING - Failed to verify tasks: {verify_result.get('error', 'Unknown error')}")

                        print("CONTAINER: Setting up git for change tracking...")

                        print("CONTAINER: Changing to /app directory...")
                        cd_result = run_command_in_container(
                            container=container,
                            command=["sh", "-c", "cd /app && pwd"],
                            stream=False,
                        )
                        if cd_result.get("exit_code") == 0:
                            print(f"CONTAINER: Working directory: {cd_result.get('output', '').strip()}")
                        else:
                            print(f"CONTAINER: Failed to verify /app directory: {cd_result.get('error', 'Unknown error')}")

                        print("CONTAINER: Configuring git user...")
                        git_config_email = run_command_in_container(
                            container=container,
                            command=["git", "config", "--global", "user.email", "test@example.com"],
                            stream=False,
                        )
                        if git_config_email.get("exit_code") != 0:
                            print(f"CONTAINER: Git email config failed: {git_config_email.get('error', 'Unknown error')}")

                        git_config_name = run_command_in_container(
                            container=container,
                            command=["git", "config", "--global", "user.name", "Test User"],
                            stream=False,
                        )
                        if git_config_name.get("exit_code") != 0:
                            print(f"CONTAINER: Git name config failed: {git_config_name.get('error', 'Unknown error')}")

                        print("CONTAINER: Configuring git settings for reliable tracking...")
                        git_configs = [
                            ["git", "config", "--global", "core.autocrlf", "false"],
                            ["git", "config", "--global", "core.safecrlf", "false"],
                            ["git", "config", "--global", "init.defaultBranch", "main"],
                            ["git", "config", "--global", "advice.detachedHead", "false"],
                        ]

                        for config_cmd in git_configs:
                            config_result = run_command_in_container(container=container, command=config_cmd, stream=False)
                            if config_result.get("exit_code") != 0:
                                print(f"CONTAINER: Git config {' '.join(config_cmd[2:])} failed: {config_result.get('error', 'Unknown error')}")

                        print("CONTAINER: Checking if git repository exists...")
                        git_check_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "rev-parse", "--git-dir"],
                            stream=False,
                        )

                        if git_check_result.get("exit_code") == 0:
                            print("CONTAINER: Git repository already exists")
                            git_log_result = run_command_in_container(
                                container=container,
                                command=["git", "-C", "/app", "log", "--oneline", "-1"],
                                stream=False,
                            )
                            if git_log_result.get("exit_code") == 0:
                                print(f"CONTAINER: Existing commit: {git_log_result.get('output', '').strip()}")
                            else:
                                print("CONTAINER: No commits in existing repository")
                        else:
                            print("CONTAINER: No git repository found, initializing...")
                            git_init_result = run_command_in_container(
                                container=container,
                                command=["git", "-C", "/app", "init"],
                                stream=False,
                            )
                            if git_init_result.get("exit_code") == 0:
                                print("CONTAINER: Git init succeeded")
                            else:
                                print(f"CONTAINER: Git init failed: {git_init_result.get('error', 'Unknown error')}")

                        git_status_check = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "status"],
                            stream=False,
                        )
                        if git_status_check.get("exit_code") == 0:
                            print("CONTAINER: Git status check passed")
                        else:
                            print(f"CONTAINER: Git status check failed: {git_status_check.get('error', 'Unknown error')}")

                        print("CONTAINER: Creating .gitignore...")
                        # Use printf with escaped newlines to avoid heredoc issues with docker exec
                        # The repr() call in docker_utils.py breaks heredoc syntax
                        gitignore_lines = [
                            "node_modules/",
                            "venv/",
                            "env/",
                            ".env",
                            "__pycache__/",
                            "*.pyc",
                            "*.pyo",
                            ".pytest_cache/",
                            "",
                            "build/",
                            "dist/",
                            "*.egg-info/",
                            "target/",
                            "",
                            "*.log",
                            "*.tmp",
                            ".DS_Store",
                            ".coverage",
                            ".cache/",
                            "",
                            "package-lock.json",
                            "package.json",
                            "yarn.lock",
                            "composer.lock",
                            "Gemfile.lock",
                            "Pipfile.lock",
                            "poetry.lock",
                            ".package-lock.json",
                            ".npm/",
                            ".yarn/",
                            "",
                            ".vscode/",
                            ".idea/",
                            "*.swp",
                            "*.swo",
                            "",
                            ".DS_Store",
                            "Thumbs.db",
                            "",
                            "*.pid",
                            "*.seed",
                            "",
                            "coverage/",
                            ".nyc_output/",
                            ".coverage",
                            "",
                            "tmp/",
                            "temp/",
                        ]
                        gitignore_content = "\\n".join(gitignore_lines)
                        gitignore_result = run_command_in_container(
                            container=container,
                            command=["sh", "-c", f"cd /app && printf '%b' '{gitignore_content}' > .gitignore"],
                            stream=False,
                        )
                        if gitignore_result.get("exit_code") != 0:
                            print(f"CONTAINER: Failed to create .gitignore: {gitignore_result.get('error', 'Unknown error')}")

                        print("CONTAINER: Checking available files...")
                        ls_result = run_command_in_container(
                            container=container,
                            command=["ls", "-la", "/app/"],
                            stream=False,
                        )
                        if ls_result.get("exit_code") == 0:
                            print(f"CONTAINER: Files in /app: {ls_result.get('output', '').strip()}")

                        print("CONTAINER: Adding source files to git (respecting .gitignore)...")

                        git_reset_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "reset"],
                            stream=False,
                        )
                        if git_reset_result.get("exit_code") == 0:
                            print("CONTAINER: Git reset succeeded")

                        git_add_all_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "add", "-A"],
                            stream=False,
                        )
                        if git_add_all_result.get("exit_code") == 0:
                            print("CONTAINER: Successfully added source files (respecting .gitignore)")
                        else:
                            print(f"CONTAINER: Git add -A failed: {git_add_all_result.get('error', 'Unknown error')}")

                        git_ignored_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "status", "--ignored", "--short"],
                            stream=False,
                        )
                        if git_ignored_result.get("exit_code") == 0:
                            ignored_files = git_ignored_result.get("output", "").strip()
                            if ignored_files:
                                print(f"CONTAINER: Ignored files (first 10):")
                                for line in ignored_files.split('\n')[:10]:
                                    if line.strip():
                                        print(f"CONTAINER:   {line}")
                            else:
                                print("CONTAINER: No files are being ignored by .gitignore")

                        git_status_after_add = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "status", "--porcelain"],
                            stream=False,
                        )
                        if git_status_after_add.get("exit_code") == 0:
                            status_output = git_status_after_add.get("output", "").strip()
                            if status_output:
                                print(f"CONTAINER: Files staged for commit:")
                                for line in status_output.split('\n'):
                                    print(f"CONTAINER:   {line}")
                            else:
                                print("CONTAINER: No files staged (clean working directory)")

                        git_ls_files_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "ls-files", "--stage"],
                            stream=False,
                        )
                        if git_ls_files_result.get("exit_code") == 0:
                            tracked_files = git_ls_files_result.get("output", "").strip()
                            if tracked_files:
                                file_count = len(tracked_files.split('\n'))
                                print(f"CONTAINER: Git is tracking {file_count} files")
                            else:
                                print("CONTAINER: Git is not tracking any files")

                        print("CONTAINER: Creating initial commit...")
                        git_commit_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "commit", "-m", "Initial state", "--allow-empty"],
                            stream=False,
                        )
                        if git_commit_result.get("exit_code") == 0:
                            print("CONTAINER: Initial commit created successfully")
                        else:
                            print(f"CONTAINER: Initial commit failed: {git_commit_result.get('error', 'Unknown error')}")

                        git_log_result = run_command_in_container(
                            container=container,
                            command=["git", "-C", "/app", "log", "--oneline", "-1"],
                            stream=False,
                        )
                        if git_log_result.get("exit_code") == 0:
                            print(f"CONTAINER: Initial commit: {git_log_result.get('output', '').strip()}")

                        print("CONTAINER: Git setup completed")

                        if agent != "oracle":
                            run_command_in_container(
                                container=container,
                                command=[
                                    "sh",
                                    "-c",
                                    "find tasks -type f -name 'task_diff.txt' -delete"
                                ],
                                stream=False,
                            )

                        result = run_command_in_container(
                            container=container,
                            command=[
                                "cat",
                                f"tasks/{current_task_id}/task_description.txt",
                            ],
                        )
                        task_data = parse_task_description(result["output"])
                        if (
                            not task_data["task"]
                            or not task_data["instructions"]
                            or not task_data["parser_name"]
                        ):
                            vctx.log("Task description is not valid", "error")
                            raise typer.Exit(1)

                        # Pass@k evaluation: Run k independent attempts for this task
                        task_pass_at_k_results = []

                        for attempt_num in range(1, pass_at_k + 1):
                            if pass_at_k > 1:
                                print(f"\n{'='*60}")
                                print(f"PASS@K: Attempt {attempt_num}/{pass_at_k} for task {current_task_id}")
                                print(f"{'='*60}\n")

                            vctx.log(f"Deploying agent (attempt {attempt_num}/{pass_at_k})...")

                            try:
                                agent_result = deploy_agent_in_container(
                                    container=container,
                                    agent_name=agent,
                                    task_id=current_task_id,
                                    model_name=model_name,
                                    task_data=task_data,
                                    verbose=verbose,
                                    max_iterations=max_iterations,
                                )
                            except Exception as e:
                                print(f"AGENT DEPLOYMENT FAILED WITH EXCEPTION: {type(e).__name__}: {str(e)}")
                                tb_string = traceback.format_exc()
                                sanitized_tb = sanitize_traceback(tb_string)
                                print(f"Traceback: {sanitized_tb}")

                                agent_result = {
                                    "success": False,
                                    "error": f"Agent crashed: {str(e)}",
                                    "conversation_history": [],
                                }

                            vctx.log(f"Agent deployment result: {agent_result}", "debug")


                            if pass_at_k == 1:
                                pretty_print_conversation(agent_result, verbose)

                            vctx.log(f"Running grading (attempt {attempt_num}/{pass_at_k})...")

                            test_type = task_data.get("parser_name")
                            task_test_dir = dataset_dir / "tasks" / current_task_id
                            if (task_test_dir / "task_tests.py").exists():
                                test_type = "pytest"
                            elif (task_test_dir / "task_tests.js").exists():
                                test_type = "jest"
                            elif (task_test_dir / "task_tests.java").exists():
                                test_type = "maven"

                            grading_result = run_grading_in_container(
                                container=container,
                                task_id=current_task_id,
                                test_type=test_type,
                                dataset_dir=str(dataset_dir),
                                agent_execution_data=agent_result,
                            )
                            vctx.log(
                                f"{current_task_id} grading result (attempt {attempt_num}): {grading_result}",
                                "debug",
                            )

                            # Store this attempt's result
                            attempt_success = grading_result.get("success", False)
                            attempt_tests_passed = grading_result.get("tests_passed", 0)
                            attempt_total_tests = grading_result.get("total_tests", 0)
                            attempt_pass_rate = grading_result.get("pass_rate", 0)

                            task_pass_at_k_results.append({
                                "attempt": attempt_num,
                                "success": attempt_success,
                                "tests_passed": attempt_tests_passed,
                                "total_tests": attempt_total_tests,
                                "pass_rate": attempt_pass_rate,
                                "agent_result": agent_result,
                                "grading_result": grading_result,
                            })

                            # Log attempt result
                            if pass_at_k > 1:
                                status = "PASS" if attempt_success else "FAIL"
                                print(f"\nPASS@K Attempt {attempt_num}/{pass_at_k}: {status}")
                                print(f"       Tests: {attempt_tests_passed}/{attempt_total_tests} ({attempt_pass_rate:.1%})")

                            if attempt_success and pass_at_k > 1 and attempt_num < pass_at_k:
                                print(f"\nEarly exit: Attempt {attempt_num} passed all tests")
                                try:
                                    container.stop()
                                    container.remove()
                                except Exception as e:
                                    print(f"Warning: Failed to clean up container: {e}")
                                break

                            if attempt_num < pass_at_k:
                                try:
                                    container.stop()
                                    container.remove()
                                except Exception as e:
                                    print(f"Warning: Failed to clean up container after attempt {attempt_num}: {e}")

                                # Create fresh container for next attempt
                                print(f"\nPASS@K: Creating fresh container for attempt {attempt_num + 1}...")
                                container = client.containers.run(
                                    image.id,
                                    detach=True,
                                    entrypoint=["/bin/sh", "-c"],
                                    command=["tail -f /dev/null"],
                                    environment=env_vars,
                                )

                                try:
                                    container.reload()
                                    if container.status != "running":
                                        container.start()
                                        container.reload()
                                except Exception as e:
                                    pass

                                # Quick git setup for new container (abbreviated version)
                                run_command_in_container(container, ["git", "config", "--global", "user.email", "test@example.com"], stream=False)
                                run_command_in_container(container, ["git", "config", "--global", "user.name", "Test User"], stream=False)
                                run_command_in_container(container, ["git", "config", "--global", "core.autocrlf", "false"], stream=False)
                                run_command_in_container(container, ["git", "config", "--global", "init.defaultBranch", "main"], stream=False)
                                run_command_in_container(container, ["git", "-C", "/app", "init"], stream=False)

                                # Create .gitignore using printf to handle newlines properly through docker exec
                                gitignore_content = "node_modules/\\nvenv/\\nenv/\\n__pycache__/\\n*.pyc\\nbuild/\\ndist/\\ntarget/\\n*.log\\npackage-lock.json\\nyarn.lock\\n.vscode/\\n.idea/"
                                run_command_in_container(container, ["sh", "-c", f"cd /app && printf '%b' '{gitignore_content}' > .gitignore"], stream=False)

                                # Add and commit
                                run_command_in_container(container, ["git", "-C", "/app", "add", "-A"], stream=False)
                                run_command_in_container(container, ["git", "-C", "/app", "commit", "-m", "Initial state", "--allow-empty"], stream=False)

                                # Delete task_diff.txt for gladiator
                                if agent != "oracle":
                                    run_command_in_container(container, ["sh", "-c", "find tasks -type f -name 'task_diff.txt' -delete"], stream=False)

                        any_attempt_passed_all_tests = any(r["success"] for r in task_pass_at_k_results)
                        num_passed_attempts = sum(1 for r in task_pass_at_k_results if r["success"])

                        best_attempt = max(task_pass_at_k_results, key=lambda r: (r["tests_passed"], r["success"]))

                        if pass_at_k > 1:
                            print(f"\n{'='*60}")
                            print(f"BEST ATTEMPT: #{best_attempt['attempt']} - Showing full conversation:")
                            print(f"{'='*60}\n")
                            pretty_print_conversation(best_attempt["agent_result"], verbose)

                        grading_result = best_attempt["grading_result"]
                        agent_result = best_attempt["agent_result"]

                        success = any_attempt_passed_all_tests
                        if not success:
                            overall_success = False

                        task_tests_passed = best_attempt["tests_passed"]
                        task_total_tests = best_attempt["total_tests"]
                        total_tests_passed += task_tests_passed
                        total_tests_run += task_total_tests

                        # Store pass@k results for this task
                        all_tasks_pass_at_k_results.append({
                            "task_id": current_task_id,
                            "k": pass_at_k,
                            "attempts": task_pass_at_k_results,
                            "any_passed": any_attempt_passed_all_tests,
                            "num_passed": num_passed_attempts,
                            "best_attempt": best_attempt,
                        })

                        result = "Success" if success else "Failure"
                        failed_code_message = (
                            " Tests could not be run, agent code may be invalid or missed critical spec."
                            if grading_result["total_tests"] == 0
                            else ""
                        )

                        pass_rate = grading_result.get("pass_rate", 0)
                        meets_reqs = grading_result.get("meets_minimum_requirements", False)

                        # Print summary based on pass@k
                        if pass_at_k > 1:
                            print(f"\n{'='*60}")
                            print(f"TASK {current_task_id} PASS@{pass_at_k} SUMMARY:")
                            print(f"  Overall: {'SUCCESS' if success else 'FAILURE'} ({'At least 1' if success else 'None'} of {pass_at_k} attempts passed all tests)")
                            print(f"  Successful Attempts: {num_passed_attempts}/{pass_at_k}")
                            print(f"  Best Attempt: #{best_attempt['attempt']} with {best_attempt['tests_passed']}/{best_attempt['total_tests']} tests ({best_attempt['pass_rate']:.1%})")
                            print(f"{'='*60}")
                        else:
                            print(
                                f"TASK {current_task_id}:\t{'Success' if success else 'Failure'}.\t "
                                f"Passed {grading_result['tests_passed']}/{grading_result['total_tests']} tests "
                                f"({pass_rate:.1%}){failed_code_message}"
                            )

                        if "lab_training_data" in grading_result and grading_result["lab_training_data"]:
                            lab_data = grading_result["lab_training_data"]
                            print(f"\t-- Lab Training Metrics --")
                            print(f"\tTests Passed: {grading_result.get('exit_code') == 0}")
                            print(f"\tAgent Success: {lab_data.get('agent_execution_success', False)}")
                            print(f"\tCode Changes Made: {lab_data.get('made_code_changes', False)}")
                            print(f"\tNo Syntax Errors: {not lab_data.get('has_syntax_errors', True)}")
                            print(f"\t-- Details --")
                            print(f"\tConversation Length: {len(lab_data.get('conversation_trace', []))} steps")
                            print(f"\tSuccessful Edits: {lab_data.get('successful_edits', 0)}")
                            print(f"\tFinal Code Files: {len(lab_data.get('final_code_state', {}))} files")

                        if meets_reqs:
                            print(f"\tMeets minimum requirements (6+ tests, all pass)")
                        elif grading_result["total_tests"] < 6:
                            print(f"\tTest coverage below recommended 6+ tests")

                        for warning in grading_result.get("validation_warnings", []):
                            print(f"\t {warning}")
                        for error in grading_result.get("validation_errors", []):
                            print(f"\t {error}")

                        # Only show detailed test results for pass@1 (too verbose for pass@k)
                        if pass_at_k == 1:
                            for test_name, test_status in grading_result[
                                "test_details"
                            ].items():
                                status_icon = "pass" if test_status.value == "PASSED" else "fail"
                                print(f"\t{status_icon} {test_name}: {test_status.value}")

                        container.stop()
                        container.remove()

                    except docker.errors.DockerException as e:
                        vprint(verbose, f"Docker error: {e}", "error")
                        overall_success = False
                        raise typer.Exit(1)

        except Exception as e:
            overall_success = False
            print(f"Benchmark run failed: {e}")
            raise
        finally:
            end_time = datetime.now()
            duration = end_time - start_time

            print("-" * 60)
            print(
                f"Benchmark run completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(
                f"Total duration: {int(duration.total_seconds() // 60)}m {int(duration.total_seconds() % 60)}s"
            )
            print(f"Overall result: {'Success' if overall_success else 'Failure'}")
            print(f"Total tests: {total_tests_passed}/{total_tests_run} passed")

            # Add pass@k statistics if k > 1
            if pass_at_k > 1 and all_tasks_pass_at_k_results:
                total_tasks = len(all_tasks_pass_at_k_results)
                tasks_with_any_pass = sum(1 for t in all_tasks_pass_at_k_results if t["any_passed"])
                print(f"\nPass@{pass_at_k} Statistics:")
                print(f"  Tasks with ≥1 successful attempt: {tasks_with_any_pass}/{total_tasks} ({tasks_with_any_pass/total_tasks*100:.1f}%)")

                # Calculate average success rate across all attempts
                total_attempts = sum(len(t["attempts"]) for t in all_tasks_pass_at_k_results)
                successful_attempts = sum(t["num_passed"] for t in all_tasks_pass_at_k_results)
                if total_attempts > 0:
                    print(f"  Overall attempt success rate: {successful_attempts}/{total_attempts} ({successful_attempts/total_attempts*100:.1f}%)")

            print(f"Full log saved to: {log_file_path}")

            log_entry = create_log_entry(
                dataset=dataset,
                agent=agent,
                model=model_name,
                task_id=task_id,
                start_time=start_time,
                end_time=end_time,
                success=overall_success,
                log_file_path=str(log_file_path.name),
                tests_passed=total_tests_passed,
                total_tests=total_tests_run,
                pass_at_k=pass_at_k,
                num_passed_attempts=sum(t["num_passed"] for t in all_tasks_pass_at_k_results) if all_tasks_pass_at_k_results else None,
            )

            write_csv_log(log_entry)
            print("Summary logged to: logs/benchmark_runs.csv")


if __name__ == "__main__":
    app()
