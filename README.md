# FastAPI Dev Container with Antigravity CLI Agentic Runner

A Dockerized development environment for FastAPI projects, featuring an agentic runner (`run_agent.py`) that extracts task prompts from multiple source formats and invokes the [Antigravity CLI](https://pypi.org/project/google-antigravity/) (`agy`) to execute them autonomously.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+ — included with Docker Desktop)

## Quick Start

```bash
# Build the container image
docker compose build

# Start the container in detached mode
docker compose up -d

# Verify it's running
docker compose ps

# Stop the container
docker compose down
```

## Usage

### `run_agent.py`

The agentic runner script accepts an instruction source, extracts text content, and passes it to the Antigravity CLI.

```bash
python run_agent.py --source <path_or_url_or_notion_id>
```

#### Supported Source Formats

| Format | Example |
|---|---|
| **Text file** (`.txt`) | `python run_agent.py --source tasks/implement_login.txt` |
| **PDF file** (`.pdf`) | `python run_agent.py --source specs/api_design.pdf` |
| **Notion page URL** | `python run_agent.py --source "https://www.notion.so/My-Page-abc123..."` |
| **Notion page UUID** | `python run_agent.py --source "4a2f8c5b-8e1d-4d7a-9a1b-3c4d5e6f7a8b"` |

The runner will:
1. Auto-detect the source type from the input.
2. Extract text content (reading files, parsing PDFs via `pypdf`, or fetching from the Notion API).
3. Invoke `agy` with the extracted prompt.
4. Pass through `stdout`/`stderr` and propagate the exit code.

## Volume Mounts

The `docker-compose.yml` configures the following bind mounts:

| Host Path | Container Path | Mode | Purpose |
|---|---|---|---|
| `.` (project root) | `/workspace` | rw | Source code — live-reloads during development |
| `~/.ssh` | `/root/.ssh` | ro | SSH keys for Git operations (clone, push, pull) |
| `~/.gitconfig` | `/root/.gitconfig` | ro | Git identity (name, email) for commits |
| `~/.gemini/antigravity-cli` | `/root/.gemini/antigravity-cli` | rw | Antigravity CLI config & session history |

> **Note:** SSH and gitconfig mounts are read-only (`ro`) to protect host credentials. The Gemini config mount is read-write so the CLI can persist session state.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGY_BIN_PATH` | `agy` (on `PATH`) | Path to the Antigravity CLI binary |
| `NOTION_API_KEY` | *(none)* | Notion integration token for API access |
| `NOTION_API_URL` | `https://api.notion.com` | Base URL for the Notion API (override for testing) |
| `HOST_SSH_DIR` | `~/.ssh` | Host path to the SSH directory |
| `HOST_GITCONFIG` | `~/.gitconfig` | Host path to the `.gitconfig` file |
| `HOST_GEMINI_DIR` | `~/.gemini/antigravity-cli` | Host path to the Antigravity CLI config directory |

## Running Tests

The project uses [pytest](https://docs.pytest.org/) with a four-tier E2E test suite.

```bash
# Install test dependencies
pip install pytest

# Run all tests (uses mock container when Docker is unavailable)
pytest tests/ -v

# Run a specific tier
pytest tests/e2e/test_tier1_coverage.py -v
pytest tests/e2e/test_tier2_boundaries.py -v
pytest tests/e2e/test_tier3_combinations.py -v
pytest tests/e2e/test_tier4_workloads.py -v
```

### Test Tiers

| Tier | File | Scope |
|---|---|---|
| **Tier 1** | `test_tier1_coverage.py` | Happy-path feature coverage for all 8 core features |
| **Tier 2** | `test_tier2_boundaries.py` | Boundary & corner cases (missing files, corrupt data, permissions) |
| **Tier 3** | `test_tier3_combinations.py` | Cross-feature integration (e.g., txt → CLI pipeline) |
| **Tier 4** | `test_tier4_workloads.py` | Real-world end-to-end workflow scenarios |

> **Note:** Tests automatically fall back to a mock container stub when `docker-compose.yml` is present but Docker is not available, enabling CI environments without Docker.

## Project Structure

```
.
├── Dockerfile              # Python 3.14 slim container with system tools
├── docker-compose.yml      # Service definition with volume mounts
├── requirements.txt        # Python dependencies
├── run_agent.py            # Agentic runner script
└── tests/
    ├── conftest.py         # Shared fixtures (mock Notion server, env dirs, dev container)
    ├── e2e/
    │   ├── test_tier1_coverage.py
    │   ├── test_tier2_boundaries.py
    │   ├── test_tier3_combinations.py
    │   └── test_tier4_workloads.py
    └── mocks/
        ├── agy             # Mock agy CLI script
        └── mock_data/
            ├── sample.txt  # Sample text prompt
            └── mock_notion.json  # Mock Notion API responses
```

## License

This project is for personal / internal use.
