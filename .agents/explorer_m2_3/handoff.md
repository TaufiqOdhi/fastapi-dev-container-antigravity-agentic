# Handoff Report: Milestone 2 Docker Environment Requirements Investigation

This handoff outlines the requirements and proposed implementation strategy for Milestone 2: Docker Environment.

---

## 1. Observation

The following specifications, constraints, and instructions were directly observed from the codebase and documentation:

1. **Python Version**: `PROJECT.md` line 7:
   > `Runs Python 3.14+ with FastAPI, Uvicorn, and standard packages.`

2. **System Dependencies**: `.agents/sub_orch_m2_docker_env/SCOPE.md` lines 5-6:
   > `- Dockerfile: Python 3.14+ base image, standard dev tools (git, curl, build-essential), installation of agy CLI, and python dependencies.`

3. **Interface Contracts**: `.agents/sub_orch_m2_docker_env/SCOPE.md` lines 13-16:
   > `## Interface Contracts`
   > `- Container builds successfully.`
   > `- Python 3.14+ is present.`
   > `- FastAPI, uvicorn, python-multipart, and agy are executable.`

4. **SSH & Volume Mounts**: `TEST_INFRA.md` lines 23-29:
   > ```yaml
   >     volumes:
   >       - .:/workspace
   >       - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
   >       - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
   >       - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
   > ```
   Additionally, `TEST_INFRA.md` line 129:
   > `test_ssh_client_present: Verify ssh client is available and executable in the container.`

5. **`agy` CLI Installation Source**: `/home/hafida/.gemini/antigravity-cli/builtin/skills/antigravity_guide/references/sdk.md` lines 18-23:
   > ```sh
   > pip install google-antigravity
   > ```
   > `[IMPORTANT] The SDK relies on a compiled runtime binary that is included in the platform-specific wheels published to PyPI. Always install using pip to ensure you obtain the necessary binary.`

6. **Python Dependencies**: `.agents/sub_orch_m2_docker_env/SCOPE.md` lines 6-7:
   > `- requirements.txt: FastAPI, Uvicorn, python-multipart, pypdf, notion-client (if needed), and other dependencies.`

---

## 2. Logic Chain

Based on the direct observations above, we establish the following logical path:

1. **Base Image Selection**: Since Observation 1 specifies Python 3.14+, we must use an official Python 3.14 image. Since 3.14 is currently a release candidate/pre-release, the tag `python:3.14-rc-slim` (running Debian Bookworm) is the most suitable because it is lightweight but uses `glibc` (unlike Alpine's `musl`). According to Observation 5, the SDK/CLI utilizes a pre-compiled runtime binary that requires a standard `glibc` environment; hence, a Debian-based image is necessary.
2. **System-Level Packages**:
   - Observation 2 requires `git`, `curl`, and `build-essential`.
   - Observation 4 requires the SSH client inside the container to connect via the mounted `/root/.ssh/` key. Thus, `openssh-client` is required.
   - Because Python 3.14 is a pre-release, some packages will not have pre-built PyPI wheels and must compile from source; therefore, `build-essential` is necessary to supply GCC and development build tools.
3. **`agy` CLI source**: Observation 5 confirms that installing `google-antigravity` via `pip` installs both the SDK and the `agy` CLI binary, locating it directly on the root system `PATH` (`/usr/local/bin/agy`).
4. **Target User**: Since host configs in Observation 4 are mounted to `/root/` in the container, processes inside the container must execute as the root user.

---

## 3. Caveats

- **Python 3.14 pre-release stability**: Because Python 3.14 is in a release candidate state, some dependencies may raise warnings or require compilation from source. Including `build-essential` in the Dockerfile mitigates this.
- **Offline build limits**: In a restricted or offline network build environment, standard PyPI `pip install` commands may fail if PyPI is unreachable. In such cases, packages must be fetched via host cached folders or local wheels, though under normal build circumstances PyPI access is assumed.

---

## 4. Conclusion

We conclude that the FastAPI development environment should be implemented as follows:
1. **Dockerfile**: Base image `python:3.14-rc-slim`, installing `build-essential`, `git`, `curl`, `openssh-client`, and `ca-certificates` via apt-get, followed by pip install of python dependencies.
2. **requirements.txt**: Declaring `fastapi`, `uvicorn`, `python-multipart`, `pypdf`, `notion-client`, `google-antigravity`, and `httpx`.
The complete proposed code blocks and details are written in `/home/hafida/Projects/personal/fastapi-dev-container-antigravity-agentic/.agents/explorer_m2_3/analysis.md`.

---

## 5. Verification Method

To verify the proposed container builds successfully and matches all constraints, the following commands should be executed:

1. **Verify Dockerfile Build**:
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

*Pass Conditions*: All commands exit with code 0.
*Invalidation Conditions*: Any exit code is non-zero, Python version is < 3.14, or any package fails to import.
