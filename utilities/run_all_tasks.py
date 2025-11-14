#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


def get_task_names(dataset_path: Path) -> list:
    task_dir = dataset_path / "tasks"
    if not task_dir.exists():
        print(f"Task directory not found: {task_dir}")
        return []

    tasks = []
    for item in task_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            tasks.append(item.name)

    return sorted(tasks)


def run_task(task_name: str, dataset: str, model: str = "gpt-5") -> bool:
    cmd = [
        "uv", "run", "main.py", "bench",
        "--dataset", dataset,
        "--agent", "harness",
        "--model", model,
        "--task-id", task_name
    ]

    print(f"Running task: {task_name} with model: {model}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        success = result.returncode == 0
        status = "SUCCESS" if success else "FAILED"
        print(f"{status}: {task_name}")
        return success
    except Exception as e:
        print(f"ERROR running {task_name}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_all_tasks.py <dataset> [model]")
        sys.exit(1)

    dataset = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-5"

    print(f"Running all tasks in dataset '{dataset}' with model: {model}")

    dataset_paths = [
        Path(dataset),
        Path(f"datasets/{dataset}"),
    ]

    dataset_path = None
    for path in dataset_paths:
        if path.exists():
            dataset_path = path
            break

    if not dataset_path:
        print(f"Dataset not found! Tried paths:")
        for path in dataset_paths:
            print(f"  - {path}")
        sys.exit(1)

    print(f"Using dataset path: {dataset_path}")

    tasks = get_task_names(dataset_path)

    if not tasks:
        print("No tasks found!")
        sys.exit(1)

    print(f"Found {len(tasks)} tasks: {', '.join(tasks)}")
    print("-" * 60)

    results = {}
    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Processing task: {task}")
        success = run_task(task, dataset, model)
        results[task] = success
        print("-" * 60)

    print(f"\nSUMMARY for dataset '{dataset}' with model '{model}':")
    successful = sum(results.values())
    total = len(results)

    print(f"Successful: {successful}/{total}")
    print(f"Failed: {total - successful}/{total}")
    print(f"Success rate: {successful/total*100:.1f}%")

    print("\nDetailed results:")
    for task, success in results.items():
        status = "" if success else ""
        print(f"  {status} {task}")


if __name__ == "__main__":
    main()
