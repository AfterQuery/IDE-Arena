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


def run_task(task_name: str, dataset: str, agent: str, model: str, max_iterations: int = 35, pass_at_k: int = 1) -> bool:
    cmd = [
        "uv", "run", "main.py", "bench",
        "--dataset", dataset,
        "--agent", agent,
        "--model", model,
        "--task-id", task_name,
        "--max-iterations", str(max_iterations)
    ]

    if pass_at_k > 1:
        cmd.extend(["--pass-at", str(pass_at_k)])

    print(f"Running task: {task_name} with agent: {agent}, model: {model}")
    if pass_at_k > 1:
        print(f"Pass@{pass_at_k} evaluation: {pass_at_k} independent attempts")
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
        print("Usage: python run_all_tasks.py <dataset> [model] [--start-from task_name] [--max-iterations N] [--pass-at K]")
        sys.exit(1)

    dataset = sys.argv[1]
    model = "gpt-5"
    start_from = None
    max_iterations = 35
    pass_at_k = 1

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--start-from" and i + 1 < len(sys.argv):
            start_from = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--max-iterations" and i + 1 < len(sys.argv):
            max_iterations = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--pass-at" and i + 1 < len(sys.argv):
            pass_at_k = int(sys.argv[i + 1])
            i += 2
        else:
            model = sys.argv[i]
            i += 1

    # Determine agent based on model
    if model == "oracle":
        agent = "oracle"
        model = "oracle"
    elif model == "nullagent":
        agent = "gladiator"
        model = "nullagent"
    else:
        agent = "gladiator"

    print(f"Running tasks in dataset '{dataset}' with agent: {agent}, model: {model}")
    print(f"Max iterations per task: {max_iterations}")
    if pass_at_k > 1:
        print(f"Pass@{pass_at_k} evaluation: {pass_at_k} attempts per task")
    if start_from:
        print(f"Starting from task: {start_from}")

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

    if start_from:
        if start_from not in tasks:
            print(f"Task '{start_from}' not found in dataset!")
            print(f"Available tasks: {', '.join(tasks)}")
            sys.exit(1)

        start_index = tasks.index(start_from)
        tasks = tasks[start_index:]
        print(f"Starting from task '{start_from}' - running {len(tasks)} tasks")

    print(f"Found {len(tasks)} tasks to run: {', '.join(tasks)}")
    print("-" * 60)

    results = {}
    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Processing task: {task}")
        success = run_task(task, dataset, agent, model, max_iterations, pass_at_k)
        results[task] = success
        print("-" * 60)

    # print(f"\nSUMMARY for dataset '{dataset}' with agent '{agent}', model '{model}':")
    # successful = sum(results.values())
    # total = len(results)

    # print(f"Successful: {successful}/{total}")
    # print(f"Failed: {total - successful}/{total}")
    # print(f"Success rate: {successful/total*100:.1f}%")

    # print("\nDetailed results:")
    # for task, success in results.items():
    #     status = "yes:" if success else "no:"
    #     print(f"  {status} {task}")

if __name__ == "__main__":
    main()
