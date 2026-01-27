#!/usr/bin/env bash
set -euo pipefail

TASK_ID="${TASK_ID:-$(basename $(pwd))}"

cd /app/project
mkdir -p build
cd build
cmake .. >/dev/null
cmake --build . >/dev/null

export PYTHONPATH="${PYTHONPATH:-.}:/app"

cd /app
uv run --no-project pytest -q tests/base "tasks/${TASK_ID}/task_tests.py"
