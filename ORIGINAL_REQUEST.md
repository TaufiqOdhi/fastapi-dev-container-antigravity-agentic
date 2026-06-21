# Original User Request

## Initial Request — 2026-06-21T09:38:57Z

<USER_REQUEST>
Build a development container for FastAPI backend development containing the Antigravity CLI configured in an agentic setup, allowing it to autonomously process prompts or instructions from specified sources (like Notion cards, PDF documents, or task tickets), persisting code, configurations, and Git credentials via local directory mounts.

Working directory: ~/Projects/personal/fastapi-dev-container-antigravity-agentic
Integrity mode: benchmark

## Requirements

### R1. FastAPI Development Container Environment
The environment must be containerized using Docker and Docker Compose. The container must provide a Python environment (Python 3.14+) configured for FastAPI backend development with standard development tools installed (git, curl, build-essential).

### R2. Antigravity CLI & Agentic Runner Setup
The Antigravity CLI must be installed and executable inside the container. A runner script or utility must be provided inside the container that:
1. Accepts a source instruction/prompt document (supporting at least local `.txt` and `.pdf` files, and Notion page URLs/IDs if a mock/stub API key is provided).
2. Parses/extracts the text content from the source.
3. Invokes the Antigravity CLI with the extracted prompt to run tasks autonomously.

### R3. Volume Persistence and Host Integration
The docker-compose configuration must map volumes to persist:
1. The development workspace (source code) between the host and the container.
2. The user's host SSH keys (`~/.ssh`) and Git configuration (`~/.gitconfig`) to allow git operations inside the container.
3. The Antigravity CLI config/data directory (`~/.gemini/antigravity-cli`) so agent history, credentials, and state persist across container rebuilds.

## Acceptance Criteria

### Docker Environment & Dependencies
- [ ] Dockerfile and docker-compose.yml exist and build successfully.
- [ ] Container starts in the background and shuts down cleanly.
- [ ] Python (3.14+), fastapi, uvicorn, and python-multipart, also any other library needed for FastAPI backend developments are installed inside the container.
- [ ] All installed python libraries already documented in requirements.txt

### Agentic Runner Integration
- [ ] Antigravity CLI (`agy` or equivalent CLI) is installed and executable inside the container.
- [ ] A runner script (e.g. `run_agent.py`) exists in the container and can extract text from a test text/PDF file.
- [ ] Running the script with a test prompt correctly invokes the Antigravity CLI to process it.

### Persistence & Mounts
- [ ] Edits to files inside the container's workspace are reflected on the host.
- [ ] Host's Git config (`.gitconfig`) and SSH directories are mounted inside the container.
- [ ] Host's Antigravity CLI config directory (`~/.gemini/antigravity-cli`) is mounted and writable.

</USER_REQUEST>
