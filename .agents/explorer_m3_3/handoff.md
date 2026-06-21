# Handoff Report — Explorer Milestone 3.3

## 1. Observation
We observed the following definitions, interfaces, and E2E test constraints in the repository:
1. **Milestone Definition**: `PROJECT.md` line 15:
   `| 3 | Volume Mounts | Implement volume mounts for SSH, gitconfig, and antigravity-cli | M2 | IN_PROGRESS | cd25e655-6501-41be-9629-fd1f0ab5adc8 |`
2. **Mount Scope**: `.agents/sub_orch_m3_volume_mounts/SCOPE.md` lines 5-10:
   - Map workspace directory (`/workspace`) to the host project directory.
   - Map host SSH keys (`~/.ssh`) to `/root/.ssh` (read-only/writable as needed).
   - Map host Git configuration (`~/.gitconfig`) to `/root/.gitconfig` (read-only).
   - Map host Antigravity CLI config/data directory (`~/.gemini/antigravity-cli`) to `/root/.gemini/antigravity-cli`.
3. **Compose Service Target**: `tests/e2e/test_tier1_coverage.py` line 40:
   `full_cmd = ["docker", "compose", "exec", "dev-container"] + cmd.split()`
4. **Port Assertion**: `tests/e2e/test_tier2_boundaries.py` line 86:
   `assert "ports:" in content or "expose:" in content or "8000" in content`
5. **Isolation Environment Variables**: `TEST_INFRA.md` lines 20-29 and `tests/conftest.py` lines 218-220:
   `os.environ["HOST_SSH_DIR"] = temp_ssh`
   `os.environ["HOST_GITCONFIG"] = gitconfig_path`
   `os.environ["HOST_GEMINI_DIR"] = gemini_config_dir`

---

## 2. Logic Chain
- Based on Observation 3, the service name in `docker-compose.yml` must be `dev-container` to allow E2E tests to run commands inside the container via `docker compose exec dev-container`.
- Based on Observation 4, the port mapping or exposure of `8000` must exist inside `docker-compose.yml`.
- Based on Observation 2 and 5, we must utilize safe volume mount isolation so the test harness can redirect credential directories to temporary paths using `HOST_SSH_DIR`, `HOST_GITCONFIG`, and `HOST_GEMINI_DIR`.
- Therefore, the volumes configuration block in `docker-compose.yml` should match the snippet in `TEST_INFRA.md` precisely:
  ```yaml
  volumes:
    - .:/workspace
    - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
    - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
    - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
  ```

---

## 3. Caveats
- **Gitconfig File vs. Directory Mount**: If `~/.gitconfig` does not exist on the developer's host machine when invoking `docker compose up -d` without overriding `HOST_GITCONFIG`, Docker will default to creating a *directory* named `~/.gitconfig` on the host. This will prevent Git inside the container from reading user config. Developers should ensure a blank file exists at `~/.gitconfig` on the host prior to execution.
- **Compose Version Support**: Home directory expansion (`~`) is supported in newer Docker Compose specifications, but developers on older engines may need to configure home path environment variables explicitly.

---

## 4. Conclusion
To successfully implement Milestone 3, the project needs a `docker-compose.yml` configuration at the workspace root defining a `dev-container` service. The volumes mapping must include the codebase directory as `/workspace` and utilize `${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro`, `${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro`, and `${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli` to maintain compatibility with isolation variables used by the test runner.

---

## 5. Verification Method
- **Verification Command**: Run `pytest` on the host system.
- **Validation Criteria**: The pytest environment should execute successfully (with container fallback tests and compose configuration checks passing, specifically `test_docker_build`, `test_gitconfig_exists`, `test_ssh_dir_exists`, and `test_gemini_dir_exists`).
- **File to Inspect**: Confirm that `docker-compose.yml` contains the exact service and volume mappings outlined in `analysis.md`.
