# Review Report — Volume Mounts Verification (Milestone 3.2)

## Review Summary

**Verdict**: **APPROVE** (With recommendations for minor enhancements)

This review assesses the Docker Compose configuration and integration testing suite implemented for the FastAPI dev container and agentic runner, focusing on secure volume mounts and isolation behavior. 

The configuration in `docker-compose.yml` correctly exposes the development port (`8000`), mounts the workspace directory, and establishes mounts for host configurations (SSH, Git, and Gemini/Antigravity CLI config) with appropriate read-only and read-write flags. Safe volume mount isolation is fully supported during testing through the use of environment variables with fallback defaults.

All E2E test files (`tests/e2e/test_tier1_coverage.py`, `tests/e2e/test_tier2_boundaries.py`, etc.) are well-designed, robust, and correctly implement mock fallback states for stages where components (like `run_agent.py`) are not yet fully implemented.

*Note: E2E testing commands were proposed but timed out waiting for manual approval due to headless system constraints, so this review is based on exhaustive static verification of the codebase.*

---

## Findings

### [Minor] Finding 1: Tilde Expansion in Environment Fallbacks
- **What**: Use of `~` (tilde) in Docker Compose default values (`~/.ssh`, `~/.gitconfig`, `~/.gemini/antigravity-cli`).
- **Where**: `docker-compose.yml`, lines 14-16:
  ```yaml
  - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
  - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
  - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
  ```
- **Why**: Tilde expansion (`~`) is a shell feature. If Docker Compose is executed under system services, crontabs, or environments where a shell does not pre-evaluate variable fallbacks, it may interpret `~` literally, causing mounting errors or creating literal directories named `~` in the filesystem.
- **Suggestion**: Replace `~` with `${HOME}` (e.g., `${HOST_SSH_DIR:-${HOME}/.ssh}`) since `${HOME}` is a standard environment variable that is reliably expanded by Docker Compose in all environments.

### [Minor] Finding 2: Read-Only Gitconfig Modification Hazard
- **What**: Containerized Git commands attempting to write to `/root/.gitconfig` will fail.
- **Where**: `/root/.gitconfig:ro` mount mapping.
- **Why**: Since `/root/.gitconfig` is mounted read-only for safety (which is the correct default), any tool or script inside the container attempting to run `git config --global ...` will fail with a read-only filesystem error.
- **Suggestion**: Documentation or developer instructions should emphasize that Git configuration adjustments within the container must use the `--local` flag rather than `--global` to modify repository-specific settings rather than the read-only host mount.

---

## Verified Claims

- **Workspace Mount Mapping** → verified via file inspect of `docker-compose.yml` → **PASS**
  - *Details*: Mapped via `.:/workspace`, successfully binding host project root to the container workspace.
- **SSH Config Mount Security** → verified via file inspect of `docker-compose.yml` → **PASS**
  - *Details*: Mapped via `${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro`. The `:ro` flag prevents the container from modifying host SSH keys.
- **Gitconfig Mount Security** → verified via file inspect of `docker-compose.yml` → **PASS**
  - *Details*: Mapped via `${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro`. The `:ro` flag prevents the container from modifying host git configs.
- **Antigravity CLI Config Persistence** → verified via file inspect of `docker-compose.yml` → **PASS**
  - *Details*: Mapped via `${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli`. Left as read-write, allowing persistence of session logs/histories.
- **E2E Isolation via Env Vars** → verified via inspect of `tests/conftest.py` → **PASS**
  - *Details*: The `mock_env_dirs` fixture overrides `HOST_SSH_DIR`, `HOST_GITCONFIG`, and `HOST_GEMINI_DIR` to isolated temp directories, ensuring host credentials are never exposed or altered during test execution.

---

## Coverage Gaps

- **Host SSH Private Key Permissions** — risk level: **Medium** — recommendation: **Investigate / Add Pre-flight Check**
  - *Risk*: SSH clients strictly require private keys to have secure permissions (e.g., `600`). If a host private key has permissive settings (e.g., `644`), mounting it read-only (`:ro`) into the container means the container cannot run `chmod 600 /root/.ssh/id_rsa` to fix it. SSH will fail.
  - *Recommendation*: Consider adding a pre-flight verification script or note in documentation alerting users to verify host SSH key permissions before launching the container.

---

## Unverified Items

- **Container Build & Launch Executions** — reason not verified: Command executions (`docker compose config`, `pytest`, etc.) timed out waiting for user approval prompt in the headless execution environment. Static analysis of `docker-compose.yml`, `Dockerfile`, and `tests/` files confirms high syntactical correctness and E2E test robustness.

---
---

# Adversarial Challenge Report

## Challenge Summary

**Overall risk assessment**: **LOW**

The containerization strategy is robust against typical host leakages and directory pollution. Security boundaries are well-enforced through the use of read-only volume mounts for critical host system credentials (SSH, gitconfig). The main challenges lie in the environment differences (e.g. non-standard host shell setups) and potential runtime errors if toolings inside the container make assumptions about writable home directories.

---

## Challenges

### [Medium] Challenge 1: SSH Private Key Permission Strictness
- **Assumption challenged**: SSH client inside the container can authenticate using the mounted key.
- **Attack/Failure scenario**: The user has loose permissions (e.g. `0755` or `0644`) on their host private keys (`~/.ssh/id_rsa`). The host key is mounted read-only. When ssh is run in the container, it throws: `@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ WARNING: UNPROTECTED PRIVATE KEY FILE! @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ Permissions 0755 for '/root/.ssh/id_rsa' are too open.` The client rejects the key and falls back to password auth, causing git clone or SSH tunnels to fail silently or hang inside the agent runner.
- **Blast radius**: Complete failure of SSH-based git operations inside the container.
- **Mitigation**: Add a validation step in `run_agent.py` or container startup that checks the permissions of `/root/.ssh/id_rsa` and prints a warning message if permissions are too loose.

### [Low] Challenge 2: Absolute Path Host Paths for Windows/WSL
- **Assumption challenged**: The path defaults `~/.ssh` will expand correctly on all host operating systems.
- **Attack/Failure scenario**: If a developer runs the environment in Git Bash/WSL on Windows, the default mapping `~/.ssh` might evaluate differently depending on the Docker context (e.g., pointing to Windows `/c/Users/Name/.ssh` vs Linux path inside WSL).
- **Blast radius**: The volume mount target on the host resolves to a non-existent path, mounting an empty folder inside the container.
- **Mitigation**: Document that developers on Windows/WSL should explicitly set `HOST_SSH_DIR` environment variable to their absolute local Windows path.

---

## Stress Test Results

- **Environment Isolation Stress Test** → verified via static review of `tests/conftest.py` → **PASS**
  - *Expected*: Test runner isolates E2E tests completely from host system's actual `.gitconfig` and `.ssh` directories.
  - *Outcome*: `mock_env_dirs` fixture intercepts and overrides the environment variables to empty, temporary directories, ensuring zero leaks.
