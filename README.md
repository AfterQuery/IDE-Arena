# IDE-Bench

IDE-Bench is a comprehensive framework for evaluating AI IDE agents on real-world software engineering tasks through an IDE-native tool interface. We present a Dockerized test harness that goes beyond raw terminal execution, granting models a structured tool ecosystem that represents AI-native IDEs like Cursor and Windsurf. By providing high-level abstractions for codebase search, structured file editing, and tools for testing full-stack applications, IDE-Bench evaluates an agent’s ability to act as a true engineering collaborator. For its evaluation to prevent training data contamination, we created 80 tasks across eight never-published repositories spanning C/C++, Java, and MERN stacks, representing production scenarios including feature implementation, bug fixing, refactoring, and performance optimization that mirror daily developer workflows in private codebases. Our benchmark is the first to systematically correlate agentreported intent with successful project-level modifications in a multi-language, full-stack environment on completely uncontaminated code.

## Quick Start

### Prerequisites

- Python with `uv` package manager
- Docker running

### Running Benchmarks

**Note**: Place datasets in the `datasets/` folder (excluded from git) or use absolute paths.

**Run a Single Task**

```bash
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o --task-id task-1
```

**Run All Tasks in a Dataset**

```bash
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o
```

**Oracle Agent (Apply Golden Solution)**

The oracle agent applies the golden solution diff (`task_diff.txt`) directly to verify the test suite works:

```bash
uv run main.py --dataset /path/to/dataset --agent oracle --model oracle --task-id task-1
```

**Controlling Agent Iterations**

Limit the maximum number of iterations an agent can take using the `--max-iterations` flag (default: 35):

```bash
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o --task-id task-1 --max-iterations 50
```

**Pass@k Evaluation**

Run multiple independent attempts per task to measure success probability (default: pass@1):

```bash
# Pass@1 (default - single attempt)
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o --task-id task-1

# Pass@5 (5 independent attempts)
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o --task-id task-1 --pass-at 5
```

**How Pass@k Works:**

- Each attempt runs independently with a fresh container
- **Success**: If ANY of the k attempts passes all tests
- **Failure**: If none pass all tests, the best attempt (highest test pass count) is kept
- Accounts for non-determinism in LLM outputs
- Standard metric used in code generation research (HumanEval, Codex)

## Scaling with Kubernetes

For research and large-scale evaluations, see [k8s-setup.md](k8s-setup.md) to run hundreds of tasks in parallel on Google Kubernetes Engine.

## Environment Setup

Set your API keys:

```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
...
```

You can now run with any LiteLLM supported model tag via litellm_model_name, or use OpenRouter

## Utilities

**Run all datasets:**

```bash
uv run utilities/run_all_datasets.py <datasets_directory> [model] [--max-iterations N] [--pass-at K]
```

**Run all tasks in a dataset:**

```bash
uv run utilities/run_all_tasks.py <dataset> [model] [--start-from task_name] [--max-iterations N] [--pass-at K]
```

**Parameters:**

- `<dataset>`: Path to dataset directory (searches both absolute path and `datasets/<dataset>`)
- `[model]`: Model name (defaults to "gpt-4o"). Special values:
  - `oracle`: Uses oracle agent with oracle model
  - `nullagent`: Uses a null gladiator agent
  - Any other value: Uses gladiator agent with specified model
- `[--start-from task_name]`: Resume from a specific task (for interrupted/partial runs)
- `[--max-iterations N]`: Maximum iterations per task (default: 35)
- `[--pass-at K]`: Number of independent attempts per task for pass@k evaluation (default: 1)

## Web Interface

Start the Next.js dashboard to view traces and results:

```bash
cd app

npm i

npm run dev
```

## Dataset Structure

Each dataset contains a codebase and a set of tasks. The harness builds a Docker image from the dataset's Dockerfile, runs the agent in a container, and evaluates the agent's changes against the task's test suite.

```
dataset/
├── Dockerfile                         # Container definition for the environment
├── docker-compose.yaml                # Docker compose configuration
├── run_tests.sh                       # Global test execution script
├── project/                           # The actual codebase (structure varies by dataset)
│   └── ...
└── tasks/                             # Task definitions
    └── task-1/
        ├── task_description.txt       # Task instructions for the agent
        ├── task_diff.txt              # Golden solution diff (hidden from gladiator agents)
        ├── task_tests.py              # Test file (pytest, jest, or maven)
        ├── run-tests.sh               # Task-specific test runner
        └── docker-compose.yaml        # Task-specific container config
```

**Notes:**
- The `task_diff.txt` contains the reference solution. For non-oracle agents (gladiator), this file is automatically deleted from the container before the agent runs.
- Test files can be `task_tests.py` (pytest), `task_tests.js` (jest), or `task_tests.java` (maven).
- The harness initializes a git repository in the container to track agent changes.

## Available Agent Tools

The harness agent has access to the following IDE-like tools when solving tasks:

1. **codebase_search** - Search for code snippets using text-based keyword matching (lexical search using grep/ripgrep)
2. **read_file** - Read file contents with optional line range specification
3. **run_terminal_cmd** - Execute terminal commands in the Docker container environment
4. **list_dir** - List directory contents for exploration
5. **grep_search** - Perform regex-based searches across files using ripgrep
6. **edit_file** - Edit files using structured line-based operations (insert, replace, delete)
7. **file_search** - Search for files using fuzzy path matching
8. **delete_file** - Delete files from the workspace
