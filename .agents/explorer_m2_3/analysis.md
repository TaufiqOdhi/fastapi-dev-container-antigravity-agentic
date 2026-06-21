# Milestone 2 (Docker Environment) Requirements Analysis & Proposed Strategy

## Summary of Core Findings
The FastAPI development container requires an official Debian-based **`python:3.14-rc-slim`** base image (which provides `glibc` compatibility for `google-antigravity` precompiled binary wheels). The system packages must include **`build-essential`** (for compiling packages on Python 3.14), **`git`**, **`curl`**, and **`openssh-client`** (for SSH volume mount authentication), while the python dependencies in **`requirements.txt`** must include `fastapi`, `uvicorn`, `python-multipart`, `pypdf`, `notion-client`, and `google-antigravity` (which installs the `agy` CLI).

---

## 1. Requirements & Constraints Analysis

Based on the inspection of `PROJECT.md`, `.agents/sub_orch_m2_docker_env/SCOPE.md`, `TEST_INFRA.md`, and `antigravity-guide` offline documentation, the requirements for Milestone 2 are analyzed below.

### A. Python Base Image Selection
The project requires a **Python 3.14+** environment. Since Python 3.14 is currently a release candidate/pre-release, the official image tags on Docker Hub are under the `3.14-rc` suffix.

We analyzed the three main official image types:

| Image Variant | Operating System | libc Library | Size | Recommendation & Rationale |
|---|---|---|---|---|
| **`python:3.14-rc-slim`** | Debian Bookworm | `glibc` (Standard) | ~120MB | **RECOMMENDED**. Standard Debian allows easy package installation via `apt`, and its `glibc` runtime guarantees compatibility with the pre-compiled binary wheels shipped with the `google-antigravity` PyPI package. |
| **`python:3.14-rc`** | Debian Bookworm | `glibc` (Standard) | ~900MB | **ALTERNATIVE**. Includes build tools pre-installed but is unnecessarily large, which slows down build times and increases container footprint. |
| **`python:3.14-rc-alpine`** | Alpine Linux | `musl` libc | ~50MB | **REJECTED**. The compiled runtime binary in the `google-antigravity` Python SDK wheel targets standard Linux `glibc`. Running it on Alpine's `musl` runtime will result in binary execution and compatibility errors. |

### B. Standard Dev Tools (System-Level)
The container environment requires the following system-level tools installed via `apt-get`:

1. **`build-essential`**: Required because Python 3.14 is very new, and many third-party packages do not yet have pre-built wheels for Python 3.14 on PyPI. They must be compiled from source during the container build, requiring compilers (`gcc`, `make`, etc.) provided by `build-essential`.
2. **`git`**: Required to allow developers and agentic runners to perform Git configuration and version control tasks inside the container.
3. **`curl`**: Essential for diagnostic network requests and verifying FastAPI endpoints.
4. **`openssh-client`**: Crucial to allow the container to utilize the host SSH credentials mounted at `/root/.ssh` for remote Git actions (e.g. cloning, pushing).
5. **`ca-certificates`**: Ensures secure HTTPS requests (like fetching APIs or pip installs) verify SSL certificates correctly.

### C. `agy` CLI Installation Source & Method
According to the Antigravity Python SDK documentation (`builtin/skills/antigravity_guide/references/sdk.md`):
- The `agy` CLI is distributed as part of the **`google-antigravity`** package on PyPI.
- Running `pip install google-antigravity` installs the SDK and places the compiled `agy` binary in the standard Python script directory (which is `/usr/local/bin/agy` for root inside `python:3.14-rc-slim`, placing it directly on the default system `PATH`).
- The package relies on a compiled runtime binary shipped inside platform-specific wheels, so standard `pip` installation on a `glibc` host (Debian-based) is required.

### D. Python Dependencies (`requirements.txt`)
The `requirements.txt` file must include the following packages:

*   **`fastapi`**: The core web API framework (`PROJECT.md` line 7).
*   **`uvicorn`**: ASGI server for running the FastAPI application (`PROJECT.md` line 7).
*   **`python-multipart`**: Required by FastAPI to process form fields (`SCOPE.md` line 6).
*   **`pypdf`**: Used by the agentic runner (`run_agent.py`) to parse prompt sheets (`PROJECT.md` line 8).
*   **`notion-client`**: Required to fetch and update tasks from Notion ticket pages (`PROJECT.md` line 26).
*   **`google-antigravity`**: Provides the Python SDK and registers the `agy` executable CLI (`PROJECT.md` line 4).
*   **`httpx`**: Recommended for making asynchronous API calls during mocks and end-to-end testing (`TEST_INFRA.md` line 43).

---

## 2. Proposed Implementation Strategy

The implementation files should be written directly to the workspace root. Since this is a read-only investigation, the files are proposed here for the implementer agent.

### Proposed `Dockerfile` (Target: `/Dockerfile`)
```dockerfile
# Use the official Python 3.14 release-candidate slim base image
FROM python:3.14-rc-slim

# Set environment variables to prevent pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set the container workspace directory
WORKDIR /workspace

# Install required system tools and clean up apt cache to keep image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    openssh-client \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and building tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements file first to leverage Docker build cache
COPY requirements.txt /workspace/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default command keeps the container running in the background for development
CMD ["tail", "-f", "/dev/null"]
```

### Proposed `requirements.txt` (Target: `/requirements.txt`)
```text
fastapi>=0.115.0
uvicorn>=0.30.0
python-multipart>=0.0.9
pypdf>=4.0.0
notion-client>=2.2.1
google-antigravity>=0.1.0
httpx>=0.27.0
```

---

## 3. Verification Method

The implementer and reviewer can verify the container environment via the following commands run from the host terminal:

1.  **Build the Container**:
    ```bash
    docker build -t fastapi-dev-container -f Dockerfile .
    ```
    *Expectation*: Successful compilation and caching without dependency or build errors.

2.  **Verify Python Environment**:
    ```bash
    docker run --rm fastapi-dev-container python --version
    ```
    *Expectation*: Prints `Python 3.14.0a...` or `Python 3.14...`.

3.  **Verify System Utilities**:
    ```bash
    docker run --rm fastapi-dev-container git --version
    docker run --rm fastapi-dev-container curl --version
    docker run --rm fastapi-dev-container ssh -V
    ```
    *Expectation*: Prints version strings for all three binaries.

4.  **Verify Python Libraries and `agy` CLI**:
    ```bash
    docker run --rm fastapi-dev-container python -c "import fastapi, uvicorn, pypdf, notion, google.antigravity"
    docker run --rm fastapi-dev-container agy --help
    ```
    *Expectation*: Imports run without error (exit code 0) and the `agy --help` CLI usage instructions are printed.
