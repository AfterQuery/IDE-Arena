#!/usr/bin/env bash
set -euo pipefail
task_identifier="${1:-BASE}"

if [[ "${task_identifier}" == "BASE" ]]; then
  echo "== Running base tests =="
  pytest -q -rA tests/base
else
  echo "== Running task tests for ${task_identifier} =="
  test_file="tasks/${task_identifier}/task_tests.py"
  if [[ ! -f "${test_file}" ]]; then
    echo "Task tests not found: ${test_file}" >&2
    exit 1
  fi
  pytest -q -rA tests/base "${test_file}"
fi
