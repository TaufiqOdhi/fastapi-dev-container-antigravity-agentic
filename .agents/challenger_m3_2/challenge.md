## Challenge Summary

**Overall risk assessment**: MEDIUM

Static verification of the `docker-compose.yml` and volume configuration reveals that while standard happy-path functionality is covered, there are several edge cases where host-container integration could fail, block startup, or corrupt host permissions.

---

## Challenges

### [Medium] Challenge 1: Tilde (`~`) Path Resolution in Docker Compose Defaults
- **Assumption challenged**: Tilde (`~`) character is reliably expanded to the user's home directory by Docker Compose inside environment default values (`${HOST_SSH_DIR:-~/.ssh}`).
- **Attack scenario**: In environments where Docker Compose is executed directly without shell expansion (e.g., API clients, certain CI/CD systems, or raw compose invocations), or if `~` is interpreted literally, Docker Compose will fail to find the directory, or create a directory named `~` in the local workspace.
- **Blast radius**: The mounts will either fail to mount the real user keys, throw a compose configuration error, or create junk directories in the host workspace.
- **Mitigation**: Use `${HOME}/.ssh`, `${HOME}/.gitconfig`, and `${HOME}/.gemini/antigravity-cli` instead of `~` in default values.

### [Medium] Challenge 2: Insecure Host SSH Key Permissions under Read-Only Mount
- **Assumption challenged**: Mounted SSH keys are immediately usable regardless of host file permissions.
- **Attack scenario**: A host user has loose permissions on their `~/.ssh/id_rsa` (e.g., `0644`). When mounted into the container as read-only (`:ro`), the container cannot `chmod 600 /root/.ssh/id_rsa`. The `ssh` command inside the container will fail with "Permissions 0644 for '/root/.ssh/id_rsa' are too open."
- **Blast radius**: SSH functionality inside the container is completely broken for users with standard host key permissions.
- **Mitigation**: Use an entrypoint script to copy the mounted keys to an internal directory (e.g., `/root/.ssh_internal`) at container startup, then set `chmod 700 /root/.ssh_internal` and `chmod 600 /root/.ssh_internal/*` inside the container.

### [Medium] Challenge 3: Non-existent Host Bind Mount Targets
- **Assumption challenged**: Host `~/.gitconfig` file and `~/.gemini/antigravity-cli` directory always exist on the host machine.
- **Attack scenario**: A developer runs `docker compose up -d` on a clean host where git has never been configured (`~/.gitconfig` is missing) or where `~/.gemini` does not exist. Docker daemon automatically creates missing bind mount sources as root-owned directories.
- **Blast radius**: 
  - `~/.gitconfig` is created as a directory on the host, causing git operations in the container (which expect a file) to fail.
  - `~/.gemini/antigravity-cli` is created as a root-owned directory, making it inaccessible for writing by the host user.
- **Mitigation**: Instruct developers to run `git config --global user.name` and ensure `~/.gemini` exists before running the container, or use a script wrapper that ensures these files/folders exist on the host before running `docker compose up`.

---

## Stress Test Results

- **Defaults resolution when environment variables are unset/empty** → Defaults resolve cleanly to user home paths → If the interpreter doesn't expand `~`, compose config fails or creates a literal `~` directory → **FAIL**
- **Read-only vs. Read-write mount permission validation** → SSH and gitconfig are read-only (`:ro`), Gemini is read-write → Config mounts correctly enforce `:ro` and read-write flags → **PASS**
- **Loose permissions on host private SSH keys** → Containerized SSH client operates normally using host keys → SSH client rejects keys with loose permissions and read-only mount blocks `chmod` fix → **FAIL**
- **Non-existent host file/directory bind mounts** → Compose handles missing sources gracefully → Docker daemon creates missing paths on the host as root-owned directories, causing configuration crashes → **FAIL**

---

## Unchallenged Areas

- **E2E verification tests execution** — Commands (`docker compose build`, `docker compose up -d`, `pytest`) were not executed dynamically due to user approval timeouts for terminal command actions on the host system.
