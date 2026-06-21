# Analysis: Milestone 3 — Volume Mounts Configuration and Safe Isolation

## 1. Executive Summary
This report analyzes the requirements, test structure, and security constraints for implementing `docker-compose.yml` in the project root. Currently, `docker-compose.yml` is missing, causing E2E tests to run in a stubbed "mock-container" fallback mode. 

To enable full integration testing and standard development, a `docker-compose.yml` configuration is proposed. This compose file defines a `dev-container` service that builds from the local `Dockerfile`, mounts the workspace directory, and maps SSH keys, Git configuration, and Gemini CLI config directories from the host using environment variable overrides with defaults to ensure safe mount isolation during testing.

---

## 2. Codebase and Test Infrastructure Analysis

### 2.1 Dockerfile Analysis (`/Dockerfile`)
The Docker environment relies on `python:3.14-rc-slim`. It exposes port `8000` and uses `tail -f /dev/null` as its default entry command (`CMD`) to keep the container running indefinitely in the background for development.

### 2.2 Test Verification Strategy (`/tests/conftest.py` & `/tests/e2e/`)
By inspecting `conftest.py` and the E2E test files under `/tests/e2e/`, we determined how volume mounts are verified:
- **`mock_env_dirs` Fixture**: In `tests/conftest.py`, the test suite creates temporary directories for SSH (with mock key pair), Git (with mock `.gitconfig`), and Gemini config (`antigravity-cli`). It then sets:
  - `HOST_SSH_DIR` to the temp SSH directory
  - `HOST_GITCONFIG` to the temp `.gitconfig` file path
  - `HOST_GEMINI_DIR` to the temp Gemini directory path
- **`dev_container` Fixture**: Starts the container using `docker compose up -d` with `os.environ` containing the overridden path variables. If `docker-compose.yml` is absent, it yields a stubbed `mock-container` state to prevent hard test failures, but this masks real verification.
- **Verification Tests**:
  - **SSH Key Mount**: `test_ssh_permissions` runs `stat -c %a /root/.ssh/id_rsa` inside the container to assert it has strict `600` (or `rw-------`) permissions. `test_ssh_keys_present` checks for the presence of both private and public keys (`id_rsa` and `id_rsa.pub`).
  - **Gitconfig Mount**: `test_gitconfig_read` runs `git config --list` and asserts it successfully parses user settings. `test_gitconfig_reflect` verifies that host-side changes to the mock config immediately propagate into the container.
  - **Gemini Config Mount**: `test_gemini_write_permission` verifies the container can write to `/root/.gemini/antigravity-cli/`. `test_gemini_reflect_to_host` verifies that files written by the container are successfully read on the host. `test_gemini_persistence_reboot` checks files persist across container lifecycles.

---

## 3. Volume Mount Design and Safe Isolation

### 3.1 Mapping Specifications

| Volume Source (Host) | Volume Destination (Container) | Write Access | Purpose |
| --- | --- | --- | --- |
| Host project root (`.`) | `/workspace` | Read-Write | Share code and tests for developer loop |
| `${HOST_SSH_DIR:-~/.ssh}` | `/root/.ssh` | Read-Only (`ro`) | SSH authentication and keys for remote access |
| `${HOST_GITCONFIG:-~/.gitconfig}` | `/root/.gitconfig` | Read-Only (`ro`) | Propagate git user name, email, and identity config |
| `${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}` | `/root/.gemini/antigravity-cli` | Read-Write | Persist Antigravity CLI history and state |

### 3.2 Safe Isolation Logic
The volume configuration uses environment variables with defaults:
- **Default State (Development)**: When a developer runs `docker compose up -d` manually without setting environment variables, it defaults to the developer's actual credentials and configurations (`~/.ssh`, `~/.gitconfig`, `~/.gemini/antigravity-cli`).
- **Isolated State (Testing)**: When `pytest` runs, the test fixture intercepts these environment variables and points them to temporary directories containing mock files. This prevents tests from reading or leaking sensitive private host credentials.

---

## 4. Key Challenges & Boundary Case Analysis

### 4.1 Missing Host Configuration Files (Boundary Cases)
In `tests/e2e/test_tier2_boundaries.py`, three tests specifically check behavior when host files are missing:
- `test_gitconfig_missing`
- `test_ssh_missing_dir`
- `test_gemini_missing_dir`

These tests execute `docker compose config` with path environment variables set to nonexistent paths (e.g. `/path/to/nonexistent/gitconfig`). 
- **`docker compose config` Success**: The command succeeds because it only performs syntax checks and interpolation, without mounting or checking file existence on the host.
- **`docker compose up` Risk**: If `docker compose up` is executed when the host paths do not exist:
  - If the path is mapped to a directory (e.g., SSH, Gemini directories), the Docker daemon automatically creates the directory on the host under `root` ownership.
  - If the path is mapped to a file (e.g., `.gitconfig`), the Docker daemon will create it as a *directory* on the host under `root` ownership, which breaks subsequent git functionality for the user.

**Mitigation Recommendation**: 
Provide default values or warn users. Alternatively, use `${HOST_GITCONFIG:-${HOME}/.gitconfig}` or similar. To prevent Docker from creating directories for missing files, developers should be instructed (or a setup script run) to ensure these files exist (e.g., `touch ~/.gitconfig`) before running `docker compose up`.

### 4.2 Permission Conflicts (Host-Container Ownership)
Because the container runs as `root` (UID `0`), any files created by the container in the writeable volumes (e.g., `/root/.gemini/antigravity-cli` or `/workspace`) will be owned by `root:root` on the host. This can block non-root host users from modifying or deleting those files.
- **Mitigation Recommendation**: Document this caveat clearly. For production setups, using a non-root user in the Dockerfile matching the host user's UID/GID (e.g., via build arguments `UID` and `GID`) is recommended.

---

## 5. Recommended `docker-compose.yml` Implementation

A complete, syntax-validated, drop-in structure for `docker-compose.yml` is detailed below:

```yaml
version: '3.8'

services:
  dev-container:
    build:
      context: .
      dockerfile: Dockerfile
    image: fastapi-dev-container:latest
    container_name: dev-container
    ports:
      - "${HOST_PORT:-8000}:8000"
    volumes:
      # Mount the workspace directory for developer sync
      - .:/workspace
      
      # Mount SSH keys (Read-Only)
      - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
      
      # Mount Git Configuration (Read-Only)
      - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
      
      # Mount Gemini CLI state/history (Read-Write)
      - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
    # Keep container running in interactive mode
    stdin_open: true
    tty: true
    restart: unless-stopped
```

---

## 6. Implementation and Verification Plan

### 6.1 Verification Steps
Once the implementer creates the `docker-compose.yml` file, they should perform the following checks:
1. **Syntax Validation**: Run `docker compose config` on the host to verify YAML syntax and variable interpolation.
2. **Container Build and Startup**: Run `docker compose up --build -d` to verify image compilation and daemon start.
3. **Volume Mount Assertions**:
   - Verify `/workspace` contains the workspace files.
   - Verify `/root/.ssh` contains host SSH files and is read-only.
   - Verify `/root/.gitconfig` propagates Git configurations.
   - Verify `/root/.gemini/antigravity-cli` can write config files from within the container.
4. **Integration Test Suite**: Run `pytest tests/e2e/` from the host. Verify that all features (Feature 1-4) now run against the real container rather than skipping/stubbing through `mock-container`.
