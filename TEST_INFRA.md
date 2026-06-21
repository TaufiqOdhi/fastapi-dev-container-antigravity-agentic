# TEST_INFRA — E2E Test Suite Design and Planning

This document outlines the test harness architecture, mocking strategies, and 4-tier E2E testing test cases designed to verify the containerized FastAPI development environment and its agentic runner.

---

## 1. Test Harness Architecture

To verify the integration between the host system and the containerized FastAPI dev environment, the test harness runs **on the host** and interacts with the container environment externally. This ensures a clean, opaque-box verification track that is decoupled from the implementation details inside the container.

### Harness Components
- **Test Runner (Host)**: Written in Python using `pytest`.
- **Docker Client Interaction**: Uses Python's `subprocess` library (or `docker-py`) to execute command-line instructions (`docker compose build`, `docker compose up`, `docker compose exec`, `docker compose down`).
- **Workspace Verification**: Directly checks the local host workspace directory, which is bind-mounted to the container's workspace, verifying file propagation.
- **Isolate-and-Mock Mounts**: To protect the host developer's actual credentials (SSH keys, Git config, Gemini keys), the test harness overrides default paths using environment variables.

### Safe Volume Mount Isolation
The `docker-compose.yml` uses environment variables with defaults pointing to the actual user configurations:

```yaml
services:
  dev-container:
    build: .
    volumes:
      - .:/workspace
      - ${HOST_SSH_DIR:-~/.ssh}:/root/.ssh:ro
      - ${HOST_GITCONFIG:-~/.gitconfig}:/root/.gitconfig:ro
      - ${HOST_GEMINI_DIR:-~/.gemini/antigravity-cli}:/root/.gemini/antigravity-cli
```

During E2E testing, the host-side test harness:
1. Creates a temporary, isolated workspace directory.
2. Generates temporary directories for SSH (with a mock key pair), Git config (with test user details), and Gemini configurations.
3. Sets `HOST_SSH_DIR`, `HOST_GITCONFIG`, and `HOST_GEMINI_DIR` environment variables to point to these temporary folders.
4. Spawns the Docker Compose container using these variables.
5. Performs operations and verifies that only the temporary directories are affected.

---

## 2. Mocking Strategy

To keep testing deterministic, fast, and free of external network dependencies, we mock three key integrations: the Antigravity CLI (`agy`), the Gemini API, and the Notion API.

### Mock 1: Antigravity CLI (`agy`) Mocking
We implement a script-based mock of the `agy` executable itself.
- **Location**: `/workspace/tests/mocks/agy` (or injected via a config setting like `AGY_BIN_PATH`).
- **Mechanism**: The mock is a Python script that records all invocation arguments, environment variables, and stdin inputs to a JSON log file (`/workspace/tests/mocks/agy_invocation.json`).
- **Simulating Behavior**: The test runner can configure the mock's output, error message, and exit status code dynamically using environment variables.

Example mock implementation:
```python
#!/usr/bin/env python3
import sys
import os
import json

log_file = os.environ.get("MOCK_AGY_LOG_FILE", "/workspace/tests/mocks/agy_invocation.json")
status_code = int(os.environ.get("MOCK_AGY_EXIT_CODE", "0"))
output_text = os.environ.get("MOCK_AGY_OUTPUT", "Mock AGY Execution Successful")
error_text = os.environ.get("MOCK_AGY_ERROR", "")

invocation = {
    "args": sys.argv[1:],
    "stdin": sys.stdin.read() if not sys.stdin.isatty() else "",
    "env": {k: v for k, v in os.environ.items() if k.startswith("AGY_") or k.startswith("GEMINI_")}
}

try:
    with open(log_file, "w") as f:
        json.dump(invocation, f, indent=2)
except Exception:
    pass

if error_text:
    sys.stderr.write(error_text + "\n")

sys.stdout.write(output_text + "\n")
sys.exit(status_code)
```

### Mock 2: Gemini API Mock Server (Alternative/Advanced)
If tests require running the actual `agy` binary, we mock the Gemini API:
- **Mechanism**: A lightweight FastAPI application running in a background process inside the container or host, mocking the Gemini API endpoint schema (e.g., `/v1/models/gemini...`).
- **Configuration**: Set `GEMINI_API_BASE_URL` inside the container to point to the local mock server.

### Mock 3: Notion API Mocking
To mock Notion page retrieval without hitting `api.notion.com`:
- **Mechanism**: A local FastAPI mock Notion server run by the pytest suite (using a fixture).
- **Configuration**: The `run_agent.py` script respects a `NOTION_API_URL` environment variable. In tests, we set `NOTION_API_URL=http://localhost:8099` (or a mock service container).
- **Behavior**: Returns mock Notion block JSON objects (headers, paragraphs, lists) corresponding to requested page IDs.

---

## 3. Opaque-Box Test Tiers

### Feature Inventory
1. **Docker Container Environment**: Dev environment availability and libraries.
2. **Gitconfig Mount**: Host Git configuration sharing.
3. **SSH Mount**: Host SSH key access and permissions.
4. **Gemini Config Mount**: Persistence of CLI configurations.
5. **Text File Parsing**: Extraction of text from `.txt` files.
6. **PDF File Parsing**: Extraction of text from `.pdf` files.
7. **Notion Mocking**: URL parsing and page downloading via mock API.
8. **Antigravity CLI Invocation**: Executing the `agy` script with parsed prompt.

---

### Tier 1: Feature Coverage
At least 5 test cases per feature to verify standard happy-path functionality.

#### Feature 1: Docker Container Environment
- `test_docker_build`: Verify container builds successfully.
- `test_docker_lifecycle`: Verify container starts up in background and shuts down cleanly.
- `test_python_version`: Verify Python 3.14+ is installed inside the container.
- `test_system_binaries`: Verify system-level binaries (`git`, `curl`, `build-essential`) are installed.
- `test_python_packages`: Verify python packages (`fastapi`, `uvicorn`, `python-multipart`, `pypdf`) are installed.

#### Feature 2: Gitconfig Mount
- `test_gitconfig_exists`: Verify `.gitconfig` is present at `/root/.gitconfig` inside the container.
- `test_gitconfig_read`: Verify `git config --list` successfully parses user settings.
- `test_gitconfig_content`: Verify mounted config content matches host test config.
- `test_gitconfig_reflect`: Verify edits to test gitconfig on host immediately reflect in container.
- `test_gitconfig_integrity`: Verify git operations inside container use the mounted git identity.

#### Feature 3: SSH Mount
- `test_ssh_dir_exists`: Verify directory `/root/.ssh` is present inside the container.
- `test_ssh_permissions`: Verify the mounted private key has strict `0600` permissions inside the container.
- `test_ssh_keys_present`: Verify individual private/public key files are correctly visible.
- `test_ssh_client_present`: Verify `ssh` client is available and executable in the container.
- `test_ssh_agent_socket`: Verify the SSH agent forwarding socket is visible if configured.

#### Feature 4: Gemini Config Mount
- `test_gemini_dir_exists`: Verify `/root/.gemini/antigravity-cli` exists inside the container.
- `test_gemini_write_permission`: Verify container can write new configuration/history files to the mount.
- `test_gemini_reflect_to_host`: Verify configuration changes made inside container reflect on the host.
- `test_gemini_read_existing`: Verify CLI inside container can read pre-existing configs from the host.
- `test_gemini_persistence_reboot`: Verify configuration files persist across container stop and start.

#### Feature 5: Text File Parsing
- `test_txt_parse_simple`: Parse a single-line `.txt` file and verify extracted prompt.
- `test_txt_parse_multiline`: Parse multiline text and check line preservation.
- `test_txt_parse_utf8`: Parse UTF-8 text containing accents/emojis.
- `test_txt_parse_whitespace`: Verify trailing and leading whitespaces are stripped.
- `test_txt_parse_large`: Parse a large text document (100KB) and verify completeness.

#### Feature 6: PDF File Parsing
- `test_pdf_parse_simple`: Parse a single-page text-only PDF file.
- `test_pdf_parse_multiline`: Parse a multi-page PDF document.
- `test_pdf_parse_utf8`: Parse a PDF containing international characters.
- `test_pdf_parse_formatting`: Parse a PDF with columns and check text flow.
- `test_pdf_parse_scanned_layout`: Parse a PDF with embedded images and layout blocks, verifying layout parsing.

#### Feature 7: Notion Mocking
- `test_notion_parse_url`: Parse a valid Notion page URL and verify text extraction.
- `test_notion_parse_id`: Parse a valid Notion page UUID.
- `test_notion_block_hierarchy`: Verify paragraph, heading, and list blocks are extracted and formatted.
- `test_notion_rich_text`: Verify bold, italics, and link properties are handled gracefully.
- `test_notion_mock_auth`: Verify request authentication headers are correctly sent.

#### Feature 8: Antigravity CLI Invocation
- `test_cli_invocation_success`: Run runner script and verify it executes `agy` successfully.
- `test_cli_stdout_passthrough`: Verify stdout of `agy` is captured and printed by `run_agent.py`.
- `test_cli_stderr_passthrough`: Verify stderr of `agy` is forwarded.
- `test_cli_exit_code_propagation`: Verify runner forwards non-zero exit codes from `agy`.
- `test_cli_path_resolution`: Verify the runner locates and invokes `agy` from standard PATH.

---

### Tier 2: Boundary & Corner Cases
At least 5 test cases per feature focusing on unexpected, extreme, or faulty inputs.

#### Feature 1: Docker Container Environment
- `test_docker_env_missing_vars`: Verify startup behavior when expected env variables are unset.
- `test_docker_port_conflict`: Start container when host port 8000 is already bound (verifies port flexibility).
- `test_docker_low_resources`: Run container under restricted memory/CPU limits and verify it doesn't crash.
- `test_docker_compose_override`: Verify container configuration with an overridden compose file.
- `test_docker_abrupt_shutdown`: Kill the container process abruptly and verify workspace/config files remain uncorrupted.

#### Feature 2: Gitconfig Mount
- `test_gitconfig_missing`: Verify container starts gracefully when host `~/.gitconfig` does not exist.
- `test_gitconfig_is_directory_err`: Verify container handles host path being a directory.
- `test_gitconfig_restrictive_permissions`: Verify behavior with read-only/restrictive permissions on host gitconfig.
- `test_gitconfig_empty`: Verify behavior when the mounted gitconfig is empty.
- `test_gitconfig_unicode_comments`: Verify parsing of a gitconfig with comments containing non-ASCII symbols.

#### Feature 3: SSH Mount
- `test_ssh_missing_dir`: Verify container starts gracefully when host `~/.ssh` is absent.
- `test_ssh_empty_dir`: Verify container starts and behaves when `~/.ssh` is present but empty.
- `test_ssh_keys_insecure_perms`: Verify behavior when mounted keys have insecure permissions (e.g., 0777).
- `test_ssh_key_broken_symlink`: Verify behavior when SSH directory contains broken symbolic links.
- `test_ssh_invalid_key_formats`: Verify that corrupt SSH key files do not break container startup.

#### Feature 4: Gemini Config Mount
- `test_gemini_missing_dir`: Verify the host directory is automatically created if absent during mount.
- `test_gemini_read_only`: Verify runner behavior when config directory is mounted read-only.
- `test_gemini_corrupt_json`: Verify that the runner logs a clear error when config files contain invalid JSON.
- `test_gemini_concurrent_access`: Test concurrent write attempts from host and container.
- `test_gemini_disk_full`: Verify error logging when saving state fails due to out of space error.

#### Feature 5: Text File Parsing
- `test_txt_empty_file`: Parse a completely empty `.txt` file (should report error or exit cleanly).
- `test_txt_missing_file`: Parse a non-existent file path (must log error and exit with code 1).
- `test_txt_binary_content`: Parse a binary file disguised as `.txt` (must handle or raise encoding errors).
- `test_txt_extremely_long`: Parse a text file exceeding typical shell limits (e.g., 50MB) and verify memory limits.
- `test_txt_weird_names`: Parse files with spaces, shell wildcards, or special chars in their filenames.

#### Feature 6: PDF File Parsing
- `test_pdf_empty_pages`: Parse a PDF containing only blank pages.
- `test_pdf_corrupt`: Parse an invalid/malformed PDF file.
- `test_pdf_encrypted`: Parse a password-protected PDF.
- `test_pdf_image_only`: Parse a PDF containing only images without text layers.
- `test_pdf_huge_file`: Parse a PDF containing hundreds of pages.

#### Feature 7: Notion Mocking
- `test_notion_missing_key`: Parse a Notion URL/ID without setting the Notion API key.
- `test_notion_invalid_key`: Parse using an invalid mock key, returning a 401 Unauthorized.
- `test_notion_page_not_found`: Request a non-existent page ID, returning a 404.
- `test_notion_rate_limit_429`: Verify retries when mock Notion server returns 429 Rate Limit.
- `test_notion_empty_page`: Parse a Notion page containing no block components.

#### Feature 8: Antigravity CLI Invocation
- `test_cli_missing_binary`: Run runner when `agy` is completely missing from the system.
- `test_cli_hang`: Verify timeout handling when `agy` execution hangs.
- `test_cli_shell_injection`: Test prompt containing shell characters (`;`, `&&`, `$()`) to verify no command execution occurs.
- `test_cli_huge_args`: Test passing an exceptionally large prompt to ensure it doesn't hit system arg limits.
- `test_cli_killed`: Verify runner exits with error when `agy` is killed by SIGKILL.

---

## 3. Cross-Feature Combinations

Pairwise and multi-feature interaction test cases.

- `test_docker_gitconfig_ssh_integration`: Verify container git commands use both the mounted Git credentials and SSH keys to perform a clone/push operation against a mock SSH remote.
- `test_txt_to_cli_pipeline`: Mount a `.txt` file into the container, run `run_agent.py`, and verify that the parsed text is passed verbatim to the mock `agy` CLI.
- `test_pdf_to_cli_pipeline`: Mount a `.pdf` file into the container, run `run_agent.py`, and verify that the extracted text is passed verbatim to the mock `agy` CLI.
- `test_notion_to_cli_pipeline`: Provide a Notion URL and mock API key, retrieve the page text, and verify it is passed directly to the mock `agy` CLI.
- `test_cli_gemini_config_interaction`: Run `run_agent.py` to invoke `agy` inside the container, and verify that `agy` successfully writes history data to the mounted `/root/.gemini/antigravity-cli` directory.

---

## 4. Real-world Workloads

Realistic application scenarios to verify end-to-end functionality.

- **Scenario 1: Host-Driven Task Autopilot**
  1. A user writes a task specification to a local file `workspace/tasks/implement_login.txt` on the host.
  2. The host test harness triggers the containerized agent: `docker compose exec dev-container python run_agent.py --source /workspace/tasks/implement_login.txt`.
  3. The runner extracts the prompt, invokes `agy` (which is configured to mock a code creation operation).
  4. The mock CLI creates a FastAPI login endpoint file `/workspace/src/auth.py`.
  5. The host test harness asserts that `src/auth.py` appears in the host directory, contains valid Python syntax, and implements the expected endpoints.

- **Scenario 2: Secure Autonomous Code Release**
  1. The agent completes a task, creating a modified code file inside the container's `/workspace` directory.
  2. The runner invokes a git commit command.
  3. The containerized environment signs the commit using the mounted Git config and pushes the change to a local mock Git-over-SSH server (started as a service in docker-compose) using the mounted SSH private keys.
  4. The test harness verifies the push succeeded on the mock repository.

- **Scenario 3: Multi-Page Specification Code Generator**
  1. A developer places a multi-page PDF spec sheet of a database schema in the workspace.
  2. `run_agent.py` parses the PDF, extracts schema fields, and feeds them to the CLI.
  3. The agent implements SQLAlchemy models matching the PDF specification.
  4. The test harness runs a python script in the container to import and validate the generated models against a test SQLite database.

- **Scenario 4: Notion ticket completion cycle**
  1. A Notion page ID represents a ticket to "create a healthcheck endpoint".
  2. The runner script fetches the ticket from the mock Notion API, parses it, and feeds it to `agy`.
  3. The agent adds the healthcheck route to the FastAPI application.
  4. The runner script makes a PATCH request to the mock Notion API to update the ticket status to "Closed".
  5. The test harness verifies that:
     - The mock Notion ticket status is updated.
     - The FastAPI server in the container can be successfully queried at `/health` and returns a 200 OK.

- **Scenario 5: Persistent Agent Context Across Container Lifecycle**
  1. Run `run_agent.py` inside the container with a prompt.
  2. The CLI writes session history and context files into the mounted `/root/.gemini/antigravity-cli/history/` directory.
  3. The test harness tears down the containers (`docker compose down -v`) and rebuilds them (`docker compose up --build -d`).
  4. Run a second prompt with `run_agent.py`.
  5. Verify that the CLI successfully retrieves the previous session history from the persistent volume and refers to it in its execution logs.
