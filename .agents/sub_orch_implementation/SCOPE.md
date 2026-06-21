# Scope: Implementation Track

## Architecture
This track implements the containerized FastAPI backend development environment, volume mounts, and the agentic runner.

- **Dockerfile**: Defines the Python 3.14+ image with necessary system utilities (git, curl, build-essential) and Python requirements.
- **docker-compose.yml**: Orchestrates the dev container, mapping user configuration folders (`~/.ssh`, `~/.gitconfig`, `~/.gemini/antigravity-cli`) and the current workspace folder.
- **run_agent.py**: Extracts text from `.txt`, `.pdf`, and Notion inputs, and invokes the Antigravity CLI (`agy`).

## Milestones
| # | Name | Scope | Dependencies | Status | Conv ID |
|---|------|-------|--------------|--------|---------|
| 2 | Docker Environment | Implement Dockerfile and requirements.txt | None | DONE | f581028d-cd40-4154-870f-3aa4e3f1dbef |
| 3 | Volume Mounts | Implement docker-compose.yml with mounts for workspace, SSH, Git, and Antigravity | M2 | IN_PROGRESS | d9b09dc9-bd61-48b3-9cae-d0eece0053bc |
| 4 | Agentic Runner | Implement run_agent.py CLI and text extraction/invocation of `agy` | M2, M3 | PLANNED | TBD |
| 5 | E2E & Hardening | Verify all tests pass, and implement white-box adversarial testing (Tier 5) | M1, M2, M3, M4 | PLANNED | TBD |

## Interface Contracts
### `run_agent.py` CLI Interface
- Command: `python run_agent.py --source <path_or_url>`
- Output: Logs standard output, exits 0 on success, non-zero on error.
- Support: `.txt` files, `.pdf` files, Notion page URLs/IDs (using stub/mock logic when mock API key is provided).

## Code Layout
- `Dockerfile` - Dev container definition
- `docker-compose.yml` - Docker compose config with mounts
- `requirements.txt` - Python dependencies (FastAPI, uvicorn, python-multipart, pypdf, etc.)
- `run_agent.py` - Runner script invoking Antigravity CLI
