# Quality & Adversarial Review Report — Docker Environment

This report evaluates the `Dockerfile` and `requirements.txt` created at the root of the workspace for Milestone 2. Due to local environment constraints (permission approval prompts timed out), verification was performed primarily via thorough static code analysis and validation against the project consensus and design specifications.

---

# PART 1: Quality Review

## Review Summary

**Verdict**: APPROVE

The root `Dockerfile` and `requirements.txt` are correctly implemented, clean, minimal, and fully conform to the consensus synthesis report. They are well-suited for containerized development in this workspace.

## Findings

### [Minor] Finding 1: Running Container as Root User
- **What**: The container defaults to executing commands and scripts as the `root` user.
- **Where**: `Dockerfile:1` (implied default of base image `python:3.14-rc-slim`)
- **Why**: Running as `root` inside the container maps files to the host with `root` ownership. Since this project involves host-container mounts for SSH keys (`~/.ssh`), Git configs (`~/.gitconfig`), and Gemini history/session CLI configurations (`~/.gemini/antigravity-cli`), files written by the container to these mounted directories on the host will be owned by `root`. This can create access permission issues for the host-side developer when trying to edit or read their own configurations.
- **Suggestion**: In the upcoming docker-compose (Milestone 3), ensure mounts are either read-only (`ro`) when writes are not needed (e.g., SSH keys and gitconfig), or configure user UID/GID mapping so files written inside the container align with the host user.

### [Minor] Finding 2: Lack of Detailed Exception Handling for Compilation Dependencies
- **What**: The Dockerfile installs `build-essential` but does not include development headers like `libssl-dev` or `libffi-dev` that are often required when compiling custom C extensions from source.
- **Where**: `Dockerfile:13` (`RUN apt-get update && apt-get install -y --no-install-recommends ...`)
- **Why**: Python 3.14 is a pre-release version, so precompiled wheels for some dependencies may not exist on PyPI. If any of the required python libraries (or future ones) include compilation steps requiring cryptography or SSL headers, `build-essential` alone may not be sufficient, leading to `pip install` failures.
- **Suggestion**: If build-time failures occur on Python 3.14 due to missing C library headers, append `libssl-dev` and `libffi-dev` to the system package installation command.

## Verified Claims

- **Base Image Match** → Verified that `Dockerfile` uses `FROM python:3.14-rc-slim` → **PASS**
- **Required System Package Installation** → Verified that `Dockerfile` installs `build-essential`, `git`, `curl`, `openssh-client`, and `ca-certificates` in a single optimized layer → **PASS**
- **Docker Layer Caching** → Verified that `requirements.txt` is copied and `pip install` is executed before any other workspace code, maximizing Docker build caching → **PASS**
- **Dependency Completeness** → Verified that `requirements.txt` contains all libraries specified in `synthesis.md` (`fastapi`, `uvicorn`, `python-multipart`, `pypdf`, `notion-client`, `google-antigravity`, and `httpx`) → **PASS**
- **Minimization/Cleanup** → Verified that `apt-get` cache is cleared (`rm -rf /var/lib/apt/lists/*`) and `--no-cache-dir` is used for `pip` to optimize footprint → **PASS**

## Coverage Gaps

- **Volume Mount Validation** — Risk level: Medium — Recommendation: Volume mounts for Git/SSH/Gemini configs are mentioned in `PROJECT.md` but are not yet implemented because `docker-compose.yml` does not exist at the root. We recommend implementing and verifying these mounts in Milestone 3 to ensure permissions do not block key retrieval or writes.

## Unverified Items

- **Live Container Execution** — Reason: Command execution prompts for `docker build` and `pytest` timed out waiting for user response on the host. Build correctness and actual Python package imports were verified via static analysis only.

---

# PART 2: Adversarial Review

## Challenge Summary

**Overall risk assessment**: LOW

Statically, the Docker container configuration is robust. The primary potential failure modes reside in pre-release Python compatibility and volume mount permission lockouts.

## Challenges

### [Medium] Challenge 1: Python 3.14 Deprecation and Wheel Compilation Failures
- **Assumption challenged**: That all listed python libraries can be built and run on Python 3.14 RC.
- **Attack scenario**: Python 3.14 introduces syntax changes, deprecations, and C-API removals. If a package (or its dependencies, like a compiled parser) relies on deprecated Python internals, compilation from source will fail, or it will throw runtime `AttributeError` or `ImportError` on load.
- **Blast radius**: The Docker image fails to build, or it builds successfully but crashes when importing a package (e.g., during `fastapi` start or PDF extraction).
- **Mitigation**: Upgrading `pip`, `setuptools`, and `wheel` (implemented in `Dockerfile:22`) ensures the latest compiler compatibility. If a library fails, we should track down the specific version compatibility or fallback to a standard Python 3.13 image if necessary.

### [Medium] Challenge 2: Host CLI config corruption via Root permissions
- **Assumption challenged**: That the container can safely read/write to the mounted `~/.gemini/antigravity-cli` directory.
- **Attack scenario**: Because the container runs as `root`, any history/config files created or written by `agy` inside the container will be owned by `root`. On the host, the developer's normal user might not have permissions to overwrite or delete these root-owned files, breaking host-side CLI operations.
- **Blast radius**: Host configuration directory `/home/hafida/.gemini/antigravity-cli/` gets populated with root-owned files, causing permission-denied errors when running `agy` on the host.
- **Mitigation**: In Milestone 3, make sure that write mounts use an environment-injected UID/GID matching the host user, or verify file permissions inside the container.

## Stress Test Results

- **Run Docker Build** (`docker build -t fastapi-dev-container .`) → Expected image to build successfully → Actual: Timed out waiting for user approval prompt → **FAIL (Timeout)**
- **Check Python version** (`docker run --rm fastapi-dev-container python --version`) → Expected: `Python 3.14.x` → Actual: Timed out waiting for user approval prompt → **FAIL (Timeout)**
- **Check agy version** (`docker run --rm fastapi-dev-container agy --help`) → Expected: Help documentation for `agy` CLI → Actual: Timed out waiting for user approval prompt → **FAIL (Timeout)**

## Unchallenged Areas

- **`google-antigravity` wheel runtime features** — Reason: We do not have access to the internals of the `google-antigravity` package source or the `agy` binary to verify whether they contain hardcoded library assumptions (e.g., specific glibc minor version requirements) that could fail on Debian slim.
