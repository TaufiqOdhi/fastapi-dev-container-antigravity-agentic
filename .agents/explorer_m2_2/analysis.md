# Milestone 2 (Docker Environment) Analysis & Proposal

This document presents the requirements analysis and proposed implementation strategy for Milestone 2: Docker Environment, specifying the base image, dependencies, system tools, `agy` CLI installation, and verification methods.

---

## 1. Requirements Analysis

Milestone 2 requires implementing the `Dockerfile` and `requirements.txt` for the FastAPI development container. According to the interface contracts and design documents:
- The container must build successfully and run Python 3.14+.
- FastAPI, Uvicorn, python-multipart, and `agy` CLI must be executable inside the container.
- Volume mounts will map the host's `.ssh`, `.gitconfig`, and `.gemini/antigravity-cli` configs to the container's root directory (`/root/`).

### A. Python Base Image Selection
We recommend using **`python:3.14-rc-slim`** (or explicitly `python:3.14-rc-slim-bookworm`) as the base image.
- **Rationale**: 
  - Meets the requirement of Python 3.14+.
  - The `-slim` version keeps the container size lightweight while still using Debian Bookworm, which uses the standard `apt` package manager for easy package management.
  - Because Python 3.14 is a pre-release / release candidate, a full Ubuntu/Debian image with `apt` access is necessary to install compilers and dependency libraries.

### B. Standard Dev Tools (System-Level)
The Dockerfile must install the following standard packages via `apt-get`:
1. **`build-essential`**: Critical for Python 3.14. Since Python 3.14 is pre-release, many Python dependencies do not yet have pre-compiled wheels (binary wheels) published on PyPI. They must be compiled from source during the build process, which requires gcc, make, and other build tools provided by `build-essential`.
2. **`git`**: Required to allow the developer or agent to perform version control tasks inside the container using the mounted host `.gitconfig`.
3. **`curl`**: Standard diagnostic and testing tool for making HTTP requests (e.g. testing endpoints, fetching resources).
4. **`openssh-client`**: Required to use the mounted SSH key pair at `/root/.ssh` for authenticating Git operations against remote repositories (e.g., GitHub, GitLab).
5. **`ca-certificates`**: Ensures HTTPS requests made by Python packages or curl successfully perform SSL certificate verification.

### C. `agy` CLI Installation
- **Installation Method**: The public Python SDK and the `agy` CLI are bundled together in the PyPI package `google-antigravity`. Thus, installing the package via pip also installs the `agy` executable CLI.
- **Command**: `pip install google-antigravity`
- **Location**: Pip places the `agy` executable in the python binaries directory. For the `root` user in `python:3.14-rc-slim`, this is `/usr/local/bin/agy`, which is already in the system `PATH`.
- **Special Consideration**: Since the SDK uses a compiled runtime binary shipped as platform-specific wheels, standard pip installation is mandatory.

### D. Python Dependencies (`requirements.txt`)
The `requirements.txt` must define:
1. **`fastapi`**: The core API framework.
2. **`uvicorn`**: The ASGI server for running FastAPI.
3. **`python-multipart`**: Necessary for parsing multipart form fields in FastAPI.
4. **`pypdf`**: Used by the agentic runner (`run_agent.py`) to extract text from PDF files.
5. **`notion-client`**: Used to pull tasks directly from Notion pages via their API.
6. **`google-antigravity`**: The Antigravity Python SDK and `agy` CLI tool.
7. **`httpx`**: Highly recommended for asynchronous HTTP clients (used in tests and internal mock interactions).

---

## 2. Proposed Implementation Strategy

The implementation should be carried out in two main files located at the root of the workspace.

### A. Proposed `Dockerfile` Structure

```dockerfile
# Use the official Python 3.14 release candidate slim image
FROM python:3.14-rc-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    openssh-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel to ensure clean compilation
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy python requirements
COPY requirements.txt /workspace/

# Install python packages
RUN pip install --no-cache-dir -r requirements.txt

# Keep container running for development
CMD ["tail", "-f", "/dev/null"]
```

### B. Proposed `requirements.txt` Content

```text
fastapi>=0.110.0
uvicorn>=0.28.0
python-multipart>=0.0.9
pypdf>=4.1.0
notion-client>=2.2.1
google-antigravity>=0.1.0
httpx>=0.27.0
```

---

## 3. Verification Method

To verify the container builds successfully and implements all interface contracts, the following steps should be executed by the Worker and Reviewer:

1. **Build the container**:
   ```bash
   docker build -t fastapi-dev-container .
   ```
   *Expected outcome*: Successful build without compile errors.

2. **Verify Python version**:
   ```bash
   docker run --rm fastapi-dev-container python --version
   ```
   *Expected outcome*: `Python 3.14.0a...` or `Python 3.14...`

3. **Verify system tools are executable**:
   ```bash
   docker run --rm fastapi-dev-container git --version
   docker run --rm fastapi-dev-container curl --version
   docker run --rm fastapi-dev-container ssh -V
   ```
   *Expected outcome*: Version information printed successfully for each command.

4. **Verify Python packages and `agy` executable**:
   ```bash
   docker run --rm fastapi-dev-container python -c "import fastapi, uvicorn, pypdf, notion, google.antigravity"
   docker run --rm fastapi-dev-container agy --help
   ```
   *Expected outcome*: The import command exits with status code 0 (no ImportError), and the `agy --help` command prints the CLI help text.
