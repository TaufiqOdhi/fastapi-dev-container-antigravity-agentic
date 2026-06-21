# Handoff Report: Milestone 2 Docker Environment Requirements Exploration

This handoff contains the observations, logical inferences, conclusions, and proposed strategy for implementing the Docker environment for Milestone 2.

---

## 1. Observation

We directly observed the following constraints, requirements, and paths from the codebase and documentation:

1. **Python Version**: `PROJECT.md` line 7:
   > `Runs Python 3.14+ with FastAPI, Uvicorn, and standard packages.`

2. **System Dependencies**: `.agents/sub_orch_m2_docker_env/SCOPE.md` lines 5-6:
   > `Dockerfile: Python 3.14+ base image, standard dev tools (git, curl, build-essential), installation of agy CLI, and python dependencies.`

3. **SSH and Gitconfig Mounts**: `.agents/explorer_m1_1/test_infra_draft.md` lines 26-29:
   > ```yaml
   >       - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
   >       - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
   >       - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
   > ```
   Additionally, line 129 states:
   > `Verify ssh client is available and executable in the container.`

4. **Python Dependencies**: `.agents/sub_orch_m2_docker_env/SCOPE.md` lines 6-7:
   > `requirements.txt: FastAPI, Uvicorn, python-multipart, pypdf, notion-client (if needed), and other dependencies.`
   
   Additionally, `PROJECT.md` line 31:
   > `requirements.txt - Python dependencies (FastAPI, uvicorn, pypdf, etc.)`

5. **`agy` CLI Installation Source**: `/home/hafida/.gemini/antigravity-cli/builtin/skills/antigravity_guide/references/sdk.md` line 18:
   > `pip install google-antigravity`
   
   And lines 21-23:
   > `The SDK relies on a compiled runtime binary that is included in the platform-specific wheels published to PyPI. Always install using pip to ensure you obtain the necessary binary.`

---

## 2. Logic Chain

Based on these observations, we trace the following reasoning path to our implementation strategy:

1. **Base Image Selection**: From Observation 1, the container must use Python 3.14+. Since Python 3.14 is a pre-release version, we should choose the official pre-release tag `python:3.14-rc-slim` (which runs Debian Bookworm) to ensure standard package compatibility, keep container sizes small, and allow compiling C-extensions via standard compiler tooling.
2. **System Tools Selection**: 
   - From Observation 2, `git`, `curl`, and `build-essential` must be installed. 
   - From Observation 3, the host mounts `~/.ssh` into `/root/.ssh` inside the container and requires an `ssh` client to be present. Therefore, `openssh-client` must also be installed in the Dockerfile.
   - Because Python 3.14 is very new, many PyPI dependencies will lack binary wheels and will compile from source. Thus, `build-essential` (compiler tools) and `ca-certificates` (for secure SSL connections) are required.
3. **`agy` CLI Source**: From Observation 5, the `agy` CLI is packaged inside the `google-antigravity` PyPI module. Therefore, including `google-antigravity` in `requirements.txt` is the correct way to make both the Python SDK and `agy` executable available.
4. **Execution User**: From Observation 3, the host configuration mounts exist under the `/root/` directory (`/root/.ssh`, `/root/.gitconfig`). Consequently, the container processes must run as the `root` user to access these configurations.

---

## 3. Caveats

- **Python 3.14 Compatibility**: Because Python 3.14 is in a pre-release state, some packages might throw warnings or fail if their underlying C extensions are incompatible with the raw 3.14 C-API. In such cases, packages will need to build from source via pip, which is mitigated by including `build-essential` in the system packages.
- **Docker Compose Port Binding**: The Docker Compose service will expose FastAPI on port 8000; the test harness should be configured to handle potential port collisions gracefully.

---

## 4. Conclusion

The recommended strategy is to implement:
1. A Dockerfile using `python:3.14-rc-slim` as the base image.
2. System package installation via apt-get: `build-essential`, `git`, `curl`, `openssh-client`, `ca-certificates`.
3. Python package installation via `pip` of a `requirements.txt` containing `fastapi`, `uvicorn`, `python-multipart`, `pypdf`, `notion-client`, `google-antigravity`, and `httpx`.
4. The full details are documented in the analysis report at `/home/hafida/Projects/personal/fastapi-dev-container-antigravity-agentic/.agents/explorer_m2_2/analysis.md`.

---

## 5. Verification Method

To verify the container builds successfully and fulfills the interface requirements:

1. **Verify Build**:
   ```bash
   docker build -t fastapi-dev-container -f Dockerfile .
   ```
2. **Verify Python & executables**:
   ```bash
   docker run --rm fastapi-dev-container python --version
   docker run --rm fastapi-dev-container git --version
   docker run --rm fastapi-dev-container curl --version
   docker run --rm fastapi-dev-container ssh -V
   docker run --rm fastapi-dev-container agy --help
   ```
3. **Verify library imports**:
   ```bash
   docker run --rm fastapi-dev-container python -c "import fastapi, uvicorn, pypdf, notion, google.antigravity"
   ```
   *Pass Condition*: All commands exit with code 0.
   *Invalidation Condition*: Any command fails, any library fails to import, or the Python version is less than 3.14.
