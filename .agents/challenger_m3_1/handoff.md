# Handoff Report

## Observation

1. **Host volume default paths in docker-compose.yml (Lines 14-16)**:
   ```yaml
         - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
         - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
         - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
   ```
2. **Space-splitting and command execution in tests/e2e/test_tier1_coverage.py (Line 18 and Line 218)**:
   ```python
   def run_in_container(container_id, cmd, env=None):
       ...
       full_cmd = ["docker", "compose", "exec", "dev-container"] + cmd.split()
       res = subprocess.run(full_cmd, capture_output=True, text=True, env=env)
   ```
   and
   ```python
           run_in_container(dev_container["container_id"], "sh -c echo '{\"session\": \"mocked\"}' > /root/.gemini/antigravity-cli/container_written.json")
   ```
3. **Append redirection operator in tests/e2e/test_tier2_boundaries.py (Line 314)**:
   ```python
               run_in_container(dev_container["container_id"], "sh -c echo container >> /root/.gemini/antigravity-cli/concurrent.txt")
   ```
4. **Command execution timing out**:
   An attempt to execute `docker compose config` failed on host system with the error:
   `Encountered error in step execution: Permission prompt for action 'command' on target 'docker compose config' timed out waiting for user response.`

---

## Logic Chain

1. From Observation 4, dynamic validation cannot be run directly. Thus, we evaluate all files through static code analysis.
2. From Observation 1, the `docker-compose.yml` defaults fallback to literal paths containing a tilde `~`. Because Docker Compose does not natively perform shell tilde expansion, the default resolves to a literal directory named `~` relative to `docker-compose.yml` (e.g. `./~/.ssh/`).
3. This prevents developers from mounting their actual configurations from the host when environment variables are unset, and pollutes the workspace.
4. From Observation 2, `run_in_container` splits commands strictly by space: `cmd.split()`.
5. For the command `"sh -c echo '{\"session\": \"mocked\"}' > /root/.gemini/antigravity-cli/container_written.json"`, the split result is:
   `['sh', '-c', 'echo', '\'{"session":', '"mocked"}\'', '>', '/root/.gemini/antigravity-cli/container_written.json']`
6. Inside `subprocess.run(full_cmd, ...)`, the redirection operator `>` is passed as a literal argument instead of being processed by a shell. Additionally, the `-c` flag for `sh` only executes `echo` (the first parameter). The subsequent parameters are treated as positional arguments and ignored.
7. As a result, no file is created or written inside the container.
8. Similarly, in Observation 3, the `>>` redirection operator in `test_gemini_concurrent_access` is ignored.
9. Therefore, while these tests pass under mock mode (due to manual fixture overrides writing to the host directory directly), they will fail when run against a real container.

---

## Caveats

- We were unable to execute the compose or pytest verification command due to non-interactive environment constraints.
- `run_agent.py` was skipped in tests because it does not exist yet (to be implemented in Milestones 4 and 5).

---

## Conclusion

The `docker-compose.yml` volume mounts and the associated E2E test suites contain critical structural vulnerabilities:
1. The volume default fallbacks are broken due to reliance on literal `~` instead of `$HOME`.
2. The E2E tests are broken in non-mock mode because `run_in_container` incorrectly uses `cmd.split()` for commands containing shell redirects (`>`/`>>`) and package imports (`python3 -c "import pkg"`).
3. Missing host `.gitconfig` files will cause Docker to corrupt the host machine by creating a directory instead of a file.

---

## Verification Method

1. Run `docker compose config` with `HOST_SSH_DIR`, `HOST_GITCONFIG`, and `HOST_GEMINI_DIR` unset. Inspect the output to verify whether the paths contain a literal `~` instead of the absolute user directory.
2. Force the pytest suite to run in non-mock mode against a real container by executing:
   `pytest tests/e2e/test_tier1_coverage.py`
   Verify that tests like `test_gemini_reflect_to_host`, `test_python_packages`, and `test_gemini_concurrent_access` fail because files are not created or commands are parsed incorrectly.
