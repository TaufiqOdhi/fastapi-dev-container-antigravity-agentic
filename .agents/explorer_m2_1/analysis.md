# Milestone 2 Analysis: Docker Environment Requirements

## Executive Summary
This analysis establishes the optimal configuration for the Milestone 2 Docker environment, selecting `python:3.14-slim` as the base image to run a secure development container. Python dependencies are defined in `requirements.txt` (including `google-antigravity` to install the `agy` CLI binary), and standard dev tools (`git`, `curl`, `build-essential`) are installed to support host integration and local compilations.

---

## 1. Base Image Selection (Python 3.14+)

### Options Considered
1. **`python:3.14-slim` (Debian-based)**:
   - **Pros**: Small size (~120MB), utilizes `glibc` which ensures full compatibility with the pre-compiled platform-specific runtime binaries distributed via `google-antigravity` wheels. Includes `apt-get` for simple package management.
   - **Cons**: Requires explicit installation of git/curl/build-essential.
   - **Verdict**: **Recommended**. Safe, predictable, and robust for development and agent usage.
2. **`python:3.14` (Debian-based, Full)**:
   - **Pros**: Includes standard development tools and libraries pre-installed.
   - **Cons**: Extremely large image size (>800MB), containing unnecessary packages.
   - **Verdict**: Overkill. It is cleaner to use the slim variant and install only the required packages.
3. **`python:3.14-alpine` (Alpine-based)**:
   - **Pros**: Extremely small footprint (~50MB).
   - **Cons**: Uses `musl` libc instead of `glibc`. Pre-compiled wheels in PyPI targeting Linux usually expect `glibc` (`manylinux` tags). Compiling python packages and the `google-antigravity` SDK runtime binaries on Alpine would require complex native compiler setups and could fail or lead to non-deterministic behavior.
   - **Verdict**: Not recommended due to compatibility constraints with pre-compiled wheels.

### Recommendation
Use **`python:3.14-slim`** (or `python:3.14-rc-slim` depending on exact upstream registry availability at build time). This ensures compatibility with the standard wheels from PyPI while keeping the container footprint lean.

---

## 2. Python Dependencies in `requirements.txt`

The dependencies required to implement the specifications in `PROJECT.md` and `SCOPE.md` are:

| Package | Purpose | Version Recommendation |
|---|---|---|
| `fastapi` | Modern, fast web framework for building APIs with Python. Used for the FastAPI environment. | `fastapi>=0.115.0` |
| `uvicorn` | Production-ready ASGI web server implementation for Python. Used to run the FastAPI app. | `uvicorn>=0.30.0` |
| `python-multipart` | Required by FastAPI to parse multi-part form requests (e.g., file uploads, form inputs). | `python-multipart>=0.0.9` |
| `pypdf` | A pure-python PDF library capable of splitting, merging, cropping, and transforming pages, as well as extracting text. Used by `run_agent.py` to parse incoming `.pdf` task prompts. | `pypdf>=4.0.0` |
| `notion-client` | The official Notion SDK for Python. Needed to fetch blocks and page text from Notion page URLs/IDs for the agent runner. | `notion-client>=2.2.1` |
| `google-antigravity` | The official Google Antigravity SDK. This package contains the modules for programmatic agent leasing and compiles/installs the `agy` CLI binary on the system PATH. | Latest stable version |

---

## 3. Installation of `agy` CLI inside the Container

The Antigravity CLI (`agy`) is distributed as part of the public `google-antigravity` Python package.

### Installation Flow
1. **Standard Online Installation**:
   Adding `google-antigravity` to `requirements.txt` and running `pip install -r requirements.txt` automatically fetches the correct wheel from PyPI. The wheel includes the platform-specific compiled runtime binary required by the SDK.
   Upon installation, `pip` places the `agy` executable in the virtual environment's or system's `bin/` directory (e.g., `/usr/local/bin/agy`), making it globally accessible on the container's `PATH`.

2. **Offline/Air-gapped Alternative (CODE_ONLY constraint handling)**:
   If the build environment has restricted Internet access, the `google-antigravity` wheels or source code must be:
   - Pre-downloaded on the host and copied/mounted into the container.
   - Installed via: `pip install --no-index --find-links=/workspace/vendor/ google-antigravity` (assuming a `vendor` directory containing the downloaded wheels is placed in the workspace).

---

## 4. Standard Development Tools Verification

The following system packages must be installed in the Dockerfile using `apt-get`:

1. **`git`**:
   - **Reason**: Needed to support host-container integration for Git configurations. The container will mount the host's `~/.gitconfig` and perform Git actions under the host user's identity. Git must be present inside the container for these commands to run.
2. **`curl`**:
   - **Reason**: Needed for diagnostics, health checks, and calling API endpoints (e.g., local mock servers) inside the container.
3. **`build-essential`**:
   - **Reason**: Contains the compiler suite (gcc, g++, make, etc.) needed to compile native Python extensions if any dependency needs compilation on the target architecture.

### Dockerfile Installation Pattern
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

---

## 5. Proposed Implementation Strategy

The implementation should be carried out in two distinct files:
1. **`/workspace/requirements.txt`**: Pinning all dependencies as analyzed.
2. **`/workspace/Dockerfile`**: Building off the `python:3.14-slim` base, installing the `apt-get` packages, copying `requirements.txt`, running `pip install`, and verifying the path availability of `fastapi`, `uvicorn`, and `agy`.

Reference files containing the proposed structures are written to:
- `/home/hafida/Projects/personal/fastapi-dev-container-antigravity-agentic/.agents/explorer_m2_1/proposed_Dockerfile`
- `/home/hafida/Projects/personal/fastapi-dev-container-antigravity-agentic/.agents/explorer_m2_1/proposed_requirements.txt`
