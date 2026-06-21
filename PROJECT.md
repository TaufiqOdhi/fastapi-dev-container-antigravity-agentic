# Project: fastapi-dev-container-antigravity-agentic

## Architecture
This project establishes a containerized environment for FastAPI backend development containing an agentic runner that interfaces with the Antigravity CLI (`agy`).

- **Host-Container Integration**: Host directories (`~/.ssh`, `~/.gitconfig`, `~/.gemini/antigravity-cli`) are mounted into the container to enable SSH access, git identification, and CLI persistence.
- **FastAPI Environment**: Runs Python 3.14+ with FastAPI, Uvicorn, and standard packages.
- **Agentic Runner (`run_agent.py`)**: A Python utility that reads task prompts from various file types (`.txt`, `.pdf`, and Notion page mockups), extracts text, and invokes the Antigravity CLI.

## Milestones
| # | Name | Scope | Dependencies | Status | Conv ID |
|---|------|-------|--------------|--------|---------|
| 1 | E2E Test Suite | Design E2E testing infrastructure and implement Tiers 1-4 test cases | None | DONE | 22aeb4a1-acea-4af1-933c-0a9ebc6e7254 |
| 2 | Docker Environment | Implement Dockerfile, docker-compose.yml, and Python requirements | None | IN_PROGRESS | cd25e655-6501-41be-9629-fd1f0ab5adc8 |
| 3 | Volume Mounts | Implement volume mounts for SSH, gitconfig, and antigravity-cli | M2 | IN_PROGRESS | cd25e655-6501-41be-9629-fd1f0ab5adc8 |
| 4 | Agentic Runner | Implement Antigravity CLI and `run_agent.py` text extraction & execution | M2, M3 | IN_PROGRESS | cd25e655-6501-41be-9629-fd1f0ab5adc8 |
| 5 | E2E & Hardening | Verify all tests pass, and implement white-box adversarial testing (Tier 5) | M1, M2, M3, M4 | IN_PROGRESS | cd25e655-6501-41be-9629-fd1f0ab5adc8 |

## Interface Contracts
### `run_agent.py` CLI Interface
- Command syntax: `python run_agent.py --source <path_or_url>`
- Output: Standard output log of CLI execution, exit code 0 on success, non-zero on error.
- Supported inputs:
  - Text files (`.txt`)
  - PDF files (`.pdf`)
  - Notion URLs / IDs: Mocked or stubbed endpoint if mock API key is provided.

## Code Layout
- `Dockerfile` - Dev container definition
- `docker-compose.yml` - Docker compose config with mounts
- `requirements.txt` - Python dependencies (FastAPI, uvicorn, pypdf, etc.)
- `run_agent.py` - Runner script invoking Antigravity CLI
- `tests/` - E2E and unit tests
