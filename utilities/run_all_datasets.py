import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python run_all_datasets.py <datasets_dir> [model] [--max-iterations N] [--pass-at K]")
    sys.exit(1)

datasets_dir = Path(sys.argv[1])
model = "gpt-5"
max_iterations = None
pass_at_k = None

i = 2
while i < len(sys.argv):
    if sys.argv[i] == "--max-iterations" and i + 1 < len(sys.argv):
        max_iterations = sys.argv[i + 1]
        i += 2
    elif sys.argv[i] == "--pass-at" and i + 1 < len(sys.argv):
        pass_at_k = sys.argv[i + 1]
        i += 2
    else:
        model = sys.argv[i]
        i += 1

print(f"Running all datasets with model: {model}")
if max_iterations:
    print(f"Max iterations per task: {max_iterations}")
if pass_at_k:
    print(f"Pass@{pass_at_k} evaluation: {pass_at_k} attempts per task")

for dataset in sorted(datasets_dir.iterdir()):
    if dataset.is_dir() and not dataset.name.startswith('.'):
        cmd = ["uv", "run", "utilities/run_all_tasks.py", str(dataset), model]
        if max_iterations:
            cmd.extend(["--max-iterations", max_iterations])
        if pass_at_k:
            cmd.extend(["--pass-at", pass_at_k])
        subprocess.run(cmd)
