# Analysis & Recommendations — E2E Testing Infrastructure

This document analyzes the E2E testing boundary, potential integration risks, and provides design recommendations for the E2E Test Suite and the implementation track.

---

## 1. Problem Boundary and Scope
The goal is to design an E2E testing framework that validates the containerized FastAPI development environment and its agentic runner. Since the harness must run **on the host** and verify **containerized behavior**, the main interfaces under test are:
1. **Container lifecycle**: Creation, startup, and teardown.
2. **Mount synchronization**: Verification that files, Git config, SSH credentials, and agent configurations map cleanly between host and container.
3. **Execution correctness**: Running `run_agent.py` inside the container via host commands and validating the output/effects.

---

## 2. Key Risks and Mitigation Strategies

### Risk 1: Host Credential Mutation or Contamination
* **Problem**: Mounting the host user's actual `~/.ssh` or `~/.gitconfig` could lead to tests reading, writing, or exposing sensitive user credentials.
* **Mitigation**: Introduce environment variables in `docker-compose.yml` (`HOST_SSH_DIR`, `HOST_GITCONFIG`, `HOST_GEMINI_DIR`) that default to the host user's paths for normal development, but are overridden by the test runner to point to temporary, mock directories during E2E test execution.

### Risk 2: Non-Deterministic LLM and CLI Execution
* **Problem**: Calling the real `agy` CLI requires active Gemini API keys, costs credits, and is non-deterministic (agent responses may change over time).
* **Mitigation**: Implement a script-based mock `agy` executable inside the container. The mock log inputs (arguments, stdin) to a local JSON file and reads environment variables (such as `MOCK_AGY_EXIT_CODE` and `MOCK_AGY_OUTPUT`) to simulate various success and failure scenarios deterministically.

### Risk 3: Flaky External API Connections (Notion)
* **Problem**: The runner script needs to parse Notion page content. Relying on the real Notion API makes tests slow, fragile, and dependent on internet access.
* **Mitigation**: Add a mock mode to `run_agent.py` (e.g., triggered when `NOTION_API_KEY=mock-key` or via `NOTION_API_URL` env override) that redirects request calls to a local mock Notion server running inside the pytest framework or within the container.

### Risk 4: File Permission Mismatches (Root vs. Host User)
* **Problem**: Files created by root inside the container's `/workspace` mount will be owned by `root` on the host, causing cleanup or modification issues for the host-side test runner.
* **Mitigation**: Verify that files generated inside the workspace are cleaned up using elevated/appropriate permissions, or run the container under the same UID/GID as the host developer. Furthermore, ensure the SSH private keys generated for testing have strict permissions (`0600`) both on the host (in the temp directory) and when mounted inside the container, or SSH operations will reject them.

---

## 3. Recommended E2E Test Suite Structure

We recommend organizing the `tests/` directory in the root of the project as follows:

```
tests/
├── conftest.py               # Pytest fixtures for container spin-up, mock dirs, and mock Notion API server
├── mocks/
│   ├── agy                   # Executable python script mocking the agy CLI binary
│   └── mock_data/
│       ├── sample.txt        # Sample text prompt file
│       ├── sample.pdf        # Sample PDF prompt file
│       └── mock_notion.json  # Mock JSON responses for Notion API
├── e2e/
│   ├── test_tier1_coverage.py     # Tier 1 tests (happy-path feature coverage)
│   ├── test_tier2_boundaries.py   # Tier 2 tests (corner/boundary cases)
│   ├── test_tier3_combinations.py # Tier 3 tests (pairwise feature interactions)
│   └── test_tier4_workloads.py    # Tier 4 tests (real-world workflows)
```

### Pytest Fixture Recommendations (`conftest.py`)
1. **`mock_env_dirs`**: Creates temporary folders for SSH, gitconfig, and Gemini config, populating them with mock keypairs and dummy configuration files. Returns a dictionary of environment variables pointing to these folders.
2. **`dev_container`**: Starts the containerized environment using `docker compose up -d` with the environment variables from `mock_env_dirs` passed in, yielding the container handle, and executes `docker compose down -v` on cleanup.
3. **`mock_notion_server`**: Spawns a background FastAPI server on the host (e.g., port 8099) returning stubbed responses from `mock_notion.json` when queried, allowing `run_agent.py` inside the container to make actual HTTP calls to a mock backend.

---

## 4. Key Recommendations for the Implementer

1. **Dockerfile Configuration**:
   - Install standard PDF extraction tools or Python libraries. We suggest installing `pypdf` via `requirements.txt` as it is simple and lightweight.
   - Pre-create the `/workspace` and standard configuration directories in the Dockerfile to prevent ownership issues.

2. **`run_agent.py` Execution Flow**:
   - Use standard `argparse` for command parsing (`--source`).
   - Automatically determine the input file type by inspect of the path extension (`.txt`, `.pdf`) or URL scheme (`notion.so`).
   - When calling the `agy` CLI, do not hardcode the command path. Allow override via an environment variable `AGY_BIN_PATH` (defaulting to `agy`) to make mocking seamless.
   - Use `subprocess.run` with `text=True` and forward standard output/error stream logs.

3. **Notion Endpoint Routing**:
   - Provide an optional `NOTION_API_URL` config variable in the runner script that defaults to `https://api.notion.com/v1`. During tests, setting this to `http://localhost:8099` (or `http://host.docker.internal:8099` inside the container) directs request traffic to the mock server.
