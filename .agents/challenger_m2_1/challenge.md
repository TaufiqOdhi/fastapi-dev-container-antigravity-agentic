## Challenge Summary

**Overall risk assessment**: CRITICAL

The current Docker environment definition presents critical issues that prevent container integration and are highly likely to break container compilation under normal conditions. Specifically, the base image relies on an unstable Python pre-release, and the crucial `docker-compose.yml` configuration is missing from the workspace root, causing the test suite to fallback to mock-stub mode.

## Challenges

### [Critical] Challenge 1: Unstable Pre-release Base Image and Build Dependencies

- **Assumption challenged**: Assumes that `python:3.14-rc-slim` is a suitable and stable base image for the FastAPI development container.
- **Attack scenario**: Python 3.14 is currently a release-candidate (pre-release) version. Many compiled Python dependencies (like `pydantic-core` required by `fastapi`, and native binaries inside `google-antigravity`) do not have pre-built wheels published on PyPI for Python 3.14. During `pip install`, pip will attempt to compile these libraries from source. However:
  1. Compiling `pydantic-core` from source requires the Rust compiler (`cargo` and `rustc`), which are not installed in the Dockerfile.
  2. Compiling C/C++ extensions or Python packages from source on a pre-release Python environment often fails due to changes, deprecations, or removals in Python's internal C API.
- **Blast radius**: The `pip install` command inside the `Dockerfile` will fail to compile packages, preventing the image from building successfully.
- **Mitigation**: Use a stable, officially supported Python base image (e.g., `python:3.12-slim` or `python:3.13-slim`) for which pre-compiled wheels exist for all packages in `requirements.txt`.

### [High] Challenge 2: Missing `docker-compose.yml` Configuration

- **Assumption challenged**: Assumes that the dev container environment is fully defined by `Dockerfile` and `requirements.txt` alone, and that passing tests under fallback-mock mode verifies the Docker environment.
- **Attack scenario**: The workspace root is missing a `docker-compose.yml` file, which is required to establish host-container volume mounts (SSH keys, Git configs, and `antigravity-cli` settings/history) and environment variables as detailed in `TEST_INFRA.md`. Because `tests/conftest.py` contains a fallback fallback stub (`yield {"container_id": "mock-container", ...}`) when `docker-compose.yml` is missing, running pytest on the host will bypass actual container testing and assert only on mock behaviors.
- **Blast radius**: Host configurations (`~/.ssh`, `~/.gitconfig`, `~/.gemini/antigravity-cli`) are never mapped or tested, and developers cannot instantiate the dev environment correctly.
- **Mitigation**: Create a `docker-compose.yml` at the workspace root defining the volume mounts and environment variables as planned in `TEST_INFRA.md`.

### [Medium] Challenge 3: Lack of Local Code Copy in Dockerfile

- **Assumption challenged**: Assumes the Docker container is only executed with a local host bind-mount (`.:/workspace`) and never built as a standalone runnable image.
- **Attack scenario**: The `Dockerfile` copies `requirements.txt` but does not copy any project files (e.g. `run_agent.py` or the test suite). If this image is built and run in a CI/CD environment or production deployment where local host mounts are unavailable or restricted, the container's `/workspace` directory will be empty.
- **Blast radius**: Standalone execution of the built Docker image fails to locate and execute any application code or test scripts.
- **Mitigation**: Add a `COPY . /workspace` command (potentially behind a build target or as a fallback) to ensure code portability, or document that host mounting is strictly required for execution.

## Stress Test Results

- **Docker Image Build** → Expected: Successful build and dependency compilation → Actual/Predicted: Build fails during dependency compilation (Pydantic-core / Rust requirement, lack of python 3.14 wheels) → **FAIL**
- **Docker Compose Execution** → Expected: `docker compose up` brings up container with mounts → Actual/Predicted: Fails because `docker-compose.yml` is missing from the workspace root → **FAIL**
- **E2E Test Integration** → Expected: Pytest runs integration tests using active container → Actual/Predicted: Pytest falls back to mock-stub container execution because `docker-compose.yml` is missing, skipping actual container verification → **FAIL (Bypassed)**

## Unchallenged Areas

- **`run_agent.py` text extraction pipeline** — Not challenged because `run_agent.py` is not implemented in this milestone (part of Milestone 4).
