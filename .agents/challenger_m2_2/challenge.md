# Adversarial Review: Docker Environment Verification

**Overall risk assessment**: HIGH

---

## 1. Challenge Summary

This report documents the static and empirical verification of the Docker environment for the `fastapi-dev-container-antigravity-agentic` project. Due to command execution permissions timing out, verification was conducted through static code analysis and test infrastructure tracing. 

We identified a critical testing gap where the E2E test suite reports success even if no container exists, alongside major compatibility risks introduced by using a Python 3.14 release-candidate base image with compiled and unpinned dependencies.

---

## 2. Challenges

### [Critical] Challenge 1: Silent Test Failures via Graceful Stubs
- **Assumption challenged**: The E2E test suite (`pytest`) accurately validates the state of the containerized environment.
- **Attack scenario**: The file `docker-compose.yml` is missing from the workspace root. If the test runner runs `pytest`, the test fixture `dev_container` in `tests/conftest.py` falls back to a stubbed `mock-container` identity:
  ```python
  if not os.path.exists(compose_path):
      yield {"container_id": "mock-container", "status": "running", "root_dir": project_root}
  ```
  And `run_in_container` mocks all system command outputs:
  ```python
  if container_id == "mock-container":
      if "python3 --version" in cmd:
          return 0, "Python 3.14.0b2", ""
      ...
  ```
- **Blast radius**: The E2E tests pass with 100% success even if the Docker image fails to build, if Docker is not installed on the host, or if `docker-compose.yml` has syntax errors. This creates a false sense of security.
- **Mitigation**: The test runner should require a strict mode flag or fail the E2E test run if `docker-compose.yml` is missing, rather than silently mocking the entire container runtime.

### [High] Challenge 2: Pre-Release C-API & Wheel Incompatibility
- **Assumption challenged**: All packages listed in `requirements.txt` are installable and executable under Python 3.14.
- **Attack scenario**: The `Dockerfile` uses `FROM python:3.14-rc-slim`. `requirements.txt` requires `google-antigravity`. The Antigravity SDK reference states:
  > "The SDK relies on a compiled runtime binary that is included in the platform-specific wheels published to PyPI."
- **Blast radius**: Since Python 3.14 is in release-candidate stage, PyPI packages with compiled components (such as `google-antigravity` or other transitively compiled dependencies like `cryptography` or `pydantic-core`) often lack pre-built wheels for the new Python ABI (`cp314`). `pip install` will fail to find a wheel and attempt to compile from source, which will likely fail due to changes in C-API headers in Python 3.14.
- **Mitigation**: Standardize on a stable Python base image (e.g., `python:3.12-slim` or `python:3.13-slim`) for development unless Python 3.14 features are explicitly mandated and verified to have compatible wheels.

### [Medium] Challenge 3: Unpinned Dependencies and Drift
- **Assumption challenged**: The requirements specified in `requirements.txt` provide a reproducible, deterministic environment.
- **Attack scenario**: `requirements.txt` contains loose constraints:
  ```text
  fastapi>=0.110.0
  uvicorn>=0.28.0
  python-multipart>=0.0.9
  pypdf>=4.1.0
  notion-client>=2.2.1
  google-antigravity
  httpx>=0.27.0
  ```
- **Blast radius**: With no upper bounds or exact pin versions (and no lockfile like `requirements.lock` or `poetry.lock`), any build of the Docker container fetches the latest matching versions. This leads to configuration drift, potential breaking changes (e.g., FastAPI deprecations), or compatibility regressions under the pre-release Python 3.14 base image.
- **Mitigation**: Implement exact version pinning (e.g., `fastapi==0.115.0`) or generate a lockfile for deterministic builds.

---

## 3. Stress Test Scenarios (Predicted Behavior)

- **Scenario**: Building container on clean host without cache.
  - *Expected Behavior*: Docker builds successfully and installs all dependencies.
  - *Predicted Behavior*: **FAIL**. Compilation of `google-antigravity` or another compiled dependency fails on Python 3.14 due to missing wheels and C-API changes.
- **Scenario**: Verifying CLI `agy` execution in container.
  - *Expected Behavior*: `agy` is available and runs fine.
  - *Predicted Behavior*: **FAIL** (if build succeeds). If compiled binaries inside `google-antigravity` were built for an older Python ABI, they will fail to load in Python 3.14 with an `ImportError: undefined symbol` or segmentation fault.
- **Scenario**: Missing `docker-compose.yml`.
  - *Expected Behavior*: Test runner reports that the environment is incomplete.
  - *Predicted Behavior*: **PASS** (false positive). Pytest succeeds due to the `mock-container` fallback.

---

## 4. Unchallenged Areas

- **Host Volume Mounts (SSH, GitConfig, Gemini Config)** — Not challenged due to lack of a `docker-compose.yml` file to parse and verify volumes statically, and inability to build/run the container to verify them dynamically.
