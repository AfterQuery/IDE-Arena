import os
import sys
import time
import typer
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

app = typer.Typer()
console = Console()
load_dotenv(dotenv_path="azure.env")

def get_azure_client():
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_CONTAINER_NAME")
    if not connection_string or not container_name:
        return None, None
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
        return container_client, container_name
    except Exception:
        return None, None

def upload_logs_to_azure(dataset_path: str, agent: str, model: str, timestamp: str, stdout: str, stderr: str):
    container_client, _ = get_azure_client()
    if not container_client:
        return

    dataset_name = Path(dataset_path).name
    base_filename = f"{timestamp}/{agent}_{model}/{dataset_name}"

    try:
        if stdout:
            data = stdout.encode('utf-8')
            remainder = len(data) % 512
            if remainder > 0:
                data += b' ' * (512 - remainder)
            container_client.upload_blob(f"{base_filename}_stdout.log", data, overwrite=True, blob_type="PageBlob")

        if stderr:
            data = stderr.encode('utf-8')
            remainder = len(data) % 512
            if remainder > 0:
                data += b' ' * (512 - remainder)
            container_client.upload_blob(f"{base_filename}_stderr.log", data, overwrite=True, blob_type="PageBlob")
    except Exception:
        pass

def is_valid_dataset(path: Path) -> bool:
    return (path / "Dockerfile").exists() and (path / "tasks").exists() and (path / "run_tests.sh").exists()

def run_dataset_bench(dataset_path: str, agent: str, model: str, pass_at_k: int, max_iterations: int) -> dict:
    cmd = [
        sys.executable, "main.py", "bench",
        "--dataset", dataset_path,
        "--agent", agent,
        "--model", model,
        "--pass-at", str(pass_at_k),
        "--max-iterations", str(max_iterations)
    ]
    try:
        env = os.environ.copy()
        if "DOCKER_HOST" in env:
            del env["DOCKER_HOST"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        return {"dataset": dataset_path, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "error": None}
    except Exception as e:
        return {"dataset": dataset_path, "returncode": -1, "stdout": "", "stderr": str(e), "error": str(e)}

@app.command()
def main(
    agent: str = typer.Option("oracle"),
    model: str = typer.Option("oracle", "--model"),
    pass_at_k: int = typer.Option(1, "--pass-at"),
    max_iterations: int = typer.Option(35, "--max-iterations"),
    max_concurrent: int = typer.Option(None, "--max-concurrent"),
    verbose: bool = typer.Option(False, "--verbose"),
):
    container_client, _ = get_azure_client()
    datasets_root = Path("datasets")
    datasets = [str(path) for path in datasets_root.rglob("*") if path.is_dir() and is_valid_dataset(path)]

    if not datasets:
        raise typer.Exit(1)

    num_workers = len(datasets)
    if max_concurrent:
        num_workers = min(num_workers, max_concurrent)

    run_timestamp = time.strftime("%Y%m%d-%H%M%S")
    results = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), console=console) as progress:
        main_task = progress.add_task("Running...", total=len(datasets))
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_dataset = {executor.submit(run_dataset_bench, d, agent, model, pass_at_k, max_iterations): d for d in datasets}
            for future in as_completed(future_to_dataset):
                res = future.result()
                results.append(res)
                if container_client:
                    upload_logs_to_azure(res["dataset"], agent, model, run_timestamp, res["stdout"], res["stderr"])
                progress.advance(main_task)

    success_count = sum(1 for r in results if r["returncode"] == 0)
    print(f"Success: {success_count}/{len(datasets)}")

if __name__ == "__main__":
    app()
