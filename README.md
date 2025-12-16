# IDE Arena

IDE Arena is a comprehensive framework for evaluating AI IDE agents on real-world software engineering tasks across diverse technology stacks. We define IDE agents as AI models operating in a chat-based IDE environment with access to the same tools available in agent-enabled IDEs like Cursor. While adoption of agent-enabled IDEs is rapidly growing, there is no existing benchmark to rigorously test how well models perform as IDE agents in practice.

## Quick Start

### Prerequisites

- Python with `uv` package manager
- Docker running

### Running Benchmarks

**Note**: Place datasets in the `datasets/` folder (excluded from git) or use absolute paths.

**Oracle Agent (Golden Solution)**

```bash
uv run main.py --dataset /path_to_directory/golden --agent oracle --model oracle --task-id name_of_task
```

**AI Agent (Real Model)**

```bash
uv run main.py --dataset /path_to_directory/stubbed --agent gladiator --model litellm_model_name --task-id name_of_task
```

**Controlling Agent Iterations**

You can limit the maximum number of iterations an agent can take using the `--max-iterations` flag (default: 35):

```bash
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4 --task-id task_name --max-iterations 35
```

**Pass@k Evaluation**

Run multiple independent attempts per task to measure success probability (default: pass@1):

```bash
# Pass@1 (default - single attempt)
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o --task-id task-01

# Pass@5 (5 independent attempts)
uv run main.py --dataset /path/to/dataset --agent gladiator --model gpt-4o --task-id task-01 --pass-at 5
```

**How Pass@k Works:**

- Each attempt runs independently with a fresh container
- **Success**: If ANY of the k attempts passes all tests
- **Failure**: If none pass all tests, the best attempt (highest test pass count) is kept
- Accounts for non-determinism in LLM outputs
- Standard metric used in code generation research (HumanEval, Codex)

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
- `[model]`: Model name (defaults to "gpt-5"). Special values:
  - `oracle`: Uses oracle agent with oracle model
  - `nullagent`: Uses a null gladiator agent: nullagent
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

This project uses two distinct dataset types for evaluation:

### Golden vs Stubbed Datasets

- **Golden** (Oracle): Contains the reference implementation solutions. These are the "golden" or correct implementations that serve as the ground truth for evaluation. Golden datasets are used to establish the expected behavior and outputs.

- **Stubbed** (Null): Contains incomplete or placeholder implementations that AI agents are tested against. These are the datasets where actual evaluation occurs - AI models attempt to complete the stubbed implementations to match the golden standard.

The separation allows for:

- **Isolation**: Keeping reference solutions separate from test scenarios
- **Fair Evaluation**: AI agents work on stubbed versions without access to golden solutions
- **Reproducibility**: Golden datasets provide consistent benchmarks across evaluations

### Required Dataset Structure

Each dataset must contain the following required files and directories:

```
dataset/
├── Dockerfile                         # Container definition for the task environment
├── docker-compose.yaml                # Docker compose configuration (or compose.yaml, docker-compose.yml)
├── run_tests.sh                       # Test execution script
└── tasks/                             # Task definitions directory
    ├── task-name-1/
    │   ├── task_description.txt        # Task description and instructions
    │   ├── task_diff.txt               # Golden solution diff (for oracle mode)
    │   ├── task_tests.*                # Task/language-specific test file
    │   ├── run-tests.sh                # Task-specific test runner script
    │   └── docker-compose.yaml         # Task-specific container configuration
    ├── task-name-2/
    │   ├── task_description.txt
    │   ├── task_diff.txt
    │   ├── task_tests.*
    │   ├── run-tests.sh
    │   └── docker-compose.yaml
    └── ...
```

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
