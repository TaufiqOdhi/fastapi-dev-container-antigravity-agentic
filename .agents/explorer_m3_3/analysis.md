# Milestone 3 — Volume Mounts Analysis & Design

## 1. Executive Summary
This analysis details the design and implementation strategy for establishing host-container integration via volume mounts in `docker-compose.yml`. Key integrations include host SSH keys, Git configuration, and Gemini Antigravity CLI states, mapped to their corresponding target directories under `/root` inside the container. To ensure the host developer's credentials remain secure and untouched, a safe volume mount isolation protocol is planned using environment variables with default values, enabling seamless overriding by the E2E test suite.

---

## 2. Analysis of Volume Mount Requirements

Based on `PROJECT.md`, `SCOPE.md`, and the E2E test cases in `/tests/e2e/`, the volume mounts must be configured as follows:

| Host Source Path | Container Target Path | Access Mode | Purpose | Isolation Override Variable |
|---|---|---|---|---|
| Host Workspace Root (`.`) | `/workspace` | Read-Write | Share codebase and run agent scripts | N/A |
| `${HOST_SSH_DIR:-~/.ssh}` | `/root/.ssh` | Read-Only (`:ro`) | Git operations over SSH, key access | `HOST_SSH_DIR` |
| `${HOST_GITCONFIG:-~/.gitconfig}` | `/root/.gitconfig` | Read-Only (`:ro`) | Identify Git commit author | `HOST_GITCONFIG` |
| `${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}` | `/root/.gemini/antigravity-cli` | Read-Write | Persist Antigravity CLI configuration and history | `HOST_GEMINI_DIR` |

---

## 3. Safe Volume Mount Isolation & E2E Testing Integration

### How Isolation Works
The `docker-compose.yml` file uses shell-style environment variable substitution with defaults:
- `${VARIABLE:-default_value}`

During normal local development, the environment variables (`HOST_SSH_DIR`, etc.) are unset, and Compose defaults to the developer's actual home directories (`~/.ssh`, `~/.gitconfig`, `~/.gemini/antigravity-cli`).

During E2E testing, the host-side test runner overrides these defaults using the `mock_env_dirs` fixture (defined in `tests/conftest.py`):
1. **Host-Side Setup**: Creates temporary directories for SSH, Git, and Gemini CLI configs.
2. **Mocking Data**:
   - Generates mock private key `id_rsa` (mode `0600`) and public key `id_rsa.pub` in `temp_ssh`.
   - Writes a custom `.gitconfig` with `[user] name = Test E2E User` and `email = e2e@example.com` in `temp_git`.
   - Creates a `config.json` inside the `temp_gemini/antigravity-cli` directory.
3. **Environment Injection**: Sets environment variables `HOST_SSH_DIR`, `HOST_GITCONFIG`, and `HOST_GEMINI_DIR` to point to these temporary folders before running `docker compose up -d`.
4. **Clean Up**: Restores the original environment variables after testing concludes.

---

## 4. Critical Boundary & Corner Cases

The E2E test suite in `tests/e2e/test_tier2_boundaries.py` exercises several boundary cases that the volume mounting structure must support:

### Case 1: Missing Host Files or Directories
* **Behavior**: If `HOST_GITCONFIG` or `HOST_SSH_DIR` is set to a nonexistent path, the container must still start gracefully.
* **Analysis**: `docker compose config` evaluates the YAML syntax regardless of whether the paths exist. However, when performing `docker compose up -d`, Docker may fail if it expects a file but encounters a nonexistent path (it will default to creating a directory of that name on the host).
* **Mitigation/Recommendation**: 
  - For directories (`HOST_SSH_DIR` and `HOST_GEMINI_DIR`), Docker automatically creates the folder on the host if it does not exist.
  - For files (`HOST_GITCONFIG`), if `~/.gitconfig` does not exist on the host, mounting it directly as `${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro` will prompt Docker to create a directory named `~/.gitconfig` on the host, causing Git configuration lookup inside the container to fail (Git cannot parse a directory as a config file).
  - To prevent this, the setup instructions should recommend that local developers ensure a blank `~/.gitconfig` file exists on their host machine before bringing the container up, or the test harness must always provide a valid file when overriding.

### Case 2: Insecure Key Permissions
* **Behavior**: SSH requires private keys to have strict permissions (e.g., `0600`), failing if they are group- or world-readable (e.g., `0777`).
* **Analysis**: When mounting directories, file permissions are preserved from the host system. The E2E tests verify this via `test_ssh_permissions`, which executes `stat -c %a /root/.ssh/id_rsa` inside the container.
* **Mitigation/Recommendation**: Ensure the host-side private keys are restricted to `0600`. The test suite handles this automatically by invoking `os.chmod(private_key_path, 0o600)` on the host prior to container startup.

---

## 5. Proposed Implementation Strategy

The following YAML block represents the recommended configuration for the `docker-compose.yml` file to be placed at the project workspace root:

```yaml
version: '3.8'

services:
  dev-container:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: dev-container
    ports:
      - "8000:8000"
    volumes:
      - .:/workspace
      - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
      - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
      - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
```

### Rationale:
1. **Service Name**: Must be `dev-container` to match the exact subprocess execution target in the pytest harness (`docker compose exec dev-container`).
2. **Ports**: Port `8000:8000` is exposed to allow external API testing of the FastAPI backend and passes the port conflict boundary assertions.
3. **Volume Security**: `:ro` is appended to the SSH and Gitconfig mounts to ensure the container runs as a read-only client of these files, preventing accidental modification or corruption of developer credentials.
4. **Volume Persistence**: The `antigravity-cli` mount does not have `:ro`, allowing `agy` to persist context, configurations, and conversation history across runs.
