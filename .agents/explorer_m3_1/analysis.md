# Analysis: Volume Mounts Implementation Strategy for Docker Compose

## 1. Summary of Findings
We have analyzed the requirements and existing test suite for the volume mounts configuration in `docker-compose.yml` for Milestone 3. The service name must be `dev-container` to match the test infrastructure requirements. The volume mounts must utilize environment variables with defaults to facilitate safe isolation in tests.

## 2. Docker Compose Requirements
The containerized FastAPI development environment expects a service definition that satisfies the following:
* **Service Name**: `dev-container`. The E2E tests target this service via commands like `docker compose exec dev-container <cmd>`.
* **Port Mapping**: The FastAPI app default port is `8000`. The test suite asserts that `"ports:" in content or "expose:" in content or "8000" in content` is present in the `docker-compose.yml`.
* **Workspace Directory Mount**: The project root directory (`.`) must be mounted to `/workspace` (which matches the container's `WORKDIR` in `Dockerfile`). This needs to be read-write.
* **Host SSH directory**: Must mount `~/.ssh` (or `HOST_SSH_DIR`) to `/root/.ssh` with read-only (`:ro`) access for security.
* **Host Git config**: Must mount `~/.gitconfig` (or `HOST_GITCONFIG`) to `/root/.gitconfig` with read-only (`:ro`) access.
* **Antigravity CLI Config/Data**: Must mount `~/.gemini/antigravity-cli` (or `HOST_GEMINI_DIR`) to `/root/.gemini/antigravity-cli`. This must be read-write as the CLI and tests write history files to it.

## 3. Proposal for `docker-compose.yml`
Here is the proposed configuration block for `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  dev-container:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/workspace
      - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
      - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
      - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
```

### Key Highlights of the Proposal:
1. **Dynamic Host Path Overrides**:
   * SSH: `${HOST_SSH_DIR:-~/.ssh}` resolves to `HOST_SSH_DIR` environment variable if defined, defaulting to `~/.ssh` on the host.
   * Git config: `${HOST_GITCONFIG:-~/.gitconfig}` resolves to `HOST_GITCONFIG` if defined, defaulting to `~/.gitconfig` on the host.
   * Gemini directory: `${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}` resolves to `HOST_GEMINI_DIR` if defined, defaulting to `~/.gemini/antigravity-cli` on the host.
2. **Access Modes**:
   * SSH keys and gitconfig are mounted as read-only (`:ro`) to prevent the container from modifying sensitive credentials on the host.
   * Gemini config directory is mounted as read-write (default) to persist logs, settings, and CLI invocation histories across container rebuilds.
3. **Compatibility and Port Mapping**:
   * Binds host port `8000` to container port `8000`, fulfilling the requirements check of the E2E boundary test.

## 4. Test Isolation and Safe Mount Mechanism
Under E2E testing, the host-side test suite programmatically overrides the variables:
* A temporary directory is generated on the host.
* Mock keys/configs are generated within it (e.g. `mock_env_dirs` fixture in `conftest.py`).
* Env variables `HOST_SSH_DIR`, `HOST_GITCONFIG`, and `HOST_GEMINI_DIR` are injected pointing to these mock folders prior to spawning Docker Compose.
* Docker Compose correctly mounts these mock folders, isolating the local user's personal credentials.

## 5. Potential Caveats and Edge Cases
1. **Tilde (`~`) Resolution**:
   * Tilde expansion (`~`) is supported by modern Docker Compose (v2) but relies on correct resolution of user credentials. In systems where Docker daemon runs under a different user or context, `~` might evaluate to a path relative to the root user. If issues arise, using the `${HOME}` variable as an alternative (e.g. `${HOST_SSH_DIR:-$HOME/.ssh}`) could be recommended, but `${HOST_SSH_DIR:-~/.ssh}` is specifically mentioned in `TEST_INFRA.md`.
2. **Missing Directories/Files**:
   * If a host file or directory is missing and not overridden, Docker Compose might fail to bind mount or Docker daemon may automatically create it as a directory. The E2E tests verify that missing directory/files configurations successfully pass syntax validation (`docker compose config`).
