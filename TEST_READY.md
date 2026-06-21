# TEST_READY — E2E Test Suite Status

This document declares that the end-to-end (E2E) testing suite for the FastAPI dev container environment and agentic runner is ready. The test suite is designed as an opaque-box validation track running on the host system to verify host-container integration, volume mounts, credential sharing, and autonomous task processing.

---

## 1. Test Runner Command
To execute the complete E2E test suite, run the following command from the project root:

```bash
pytest tests/e2e/
```

Alternatively, to execute individual tiers:
- **Tier 1 (Feature Coverage)**: `pytest tests/e2e/test_tier1_coverage.py`
- **Tier 2 (Boundary Cases)**: `pytest tests/e2e/test_tier2_boundaries.py`
- **Tier 3 (Cross-Feature)**: `pytest tests/e2e/test_tier3_combinations.py`
- **Tier 4 (Workload Scenarios)**: `pytest tests/e2e/test_tier4_workloads.py`

---

## 2. Test Suite Counts

| Test Tier | Description | Test Case Count | Status |
|-----------|-------------|-----------------|--------|
| **Tier 1** | Feature Coverage (Happy-Path) | 40 | READY |
| **Tier 2** | Boundary & Corner Cases | 40 | READY |
| **Tier 3** | Cross-Feature combinations | 5 | READY |
| **Tier 4** | Real-world workload scenarios | 5 | READY |
| **Total** | **All Tiers** | **90** | **READY** |

---

## 3. Feature Coverage Checklist

Below is the status checklist of E2E tests for each of the 8 core features under test (featuring 5 Feature Coverage tests and 5 Boundary & Corner cases tests per feature):

- [x] **Docker Environment** (10 tests)
  - *Tier 1 Coverage*: `test_docker_build`, `test_docker_lifecycle`, `test_python_version`, `test_system_binaries`, `test_python_packages`
  - *Tier 2 Boundaries*: `test_docker_env_missing_vars`, `test_docker_port_conflict`, `test_docker_low_resources`, `test_docker_compose_override`, `test_docker_abrupt_shutdown`
- [x] **Gitconfig Mount** (10 tests)
  - *Tier 1 Coverage*: `test_gitconfig_exists`, `test_gitconfig_read`, `test_gitconfig_content`, `test_gitconfig_reflect`, `test_gitconfig_integrity`
  - *Tier 2 Boundaries*: `test_gitconfig_missing`, `test_gitconfig_is_directory_err`, `test_gitconfig_restrictive_permissions`, `test_gitconfig_empty`, `test_gitconfig_unicode_comments`
- [x] **SSH Mount** (10 tests)
  - *Tier 1 Coverage*: `test_ssh_dir_exists`, `test_ssh_permissions`, `test_ssh_keys_present`, `test_ssh_client_present`, `test_ssh_agent_socket`
  - *Tier 2 Boundaries*: `test_ssh_missing_dir`, `test_ssh_empty_dir`, `test_ssh_keys_insecure_perms`, `test_ssh_key_broken_symlink`, `test_ssh_invalid_key_formats`
- [x] **Gemini Config Mount** (10 tests)
  - *Tier 1 Coverage*: `test_gemini_dir_exists`, `test_gemini_write_permission`, `test_gemini_reflect_to_host`, `test_gemini_read_existing`, `test_gemini_persistence_reboot`
  - *Tier 2 Boundaries*: `test_gemini_missing_dir`, `test_gemini_read_only`, `test_gemini_corrupt_json`, `test_gemini_concurrent_access`, `test_gemini_disk_full`
- [x] **Text File Parsing** (10 tests)
  - *Tier 1 Coverage*: `test_txt_parse_simple`, `test_txt_parse_multiline`, `test_txt_parse_utf8`, `test_txt_parse_whitespace`, `test_txt_parse_large`
  - *Tier 2 Boundaries*: `test_txt_empty_file`, `test_txt_missing_file`, `test_txt_binary_content`, `test_txt_extremely_long`, `test_txt_weird_names`
- [x] **PDF File Parsing** (10 tests)
  - *Tier 1 Coverage*: `test_pdf_parse_simple`, `test_pdf_parse_multiline`, `test_pdf_parse_utf8`, `test_pdf_parse_formatting`, `test_pdf_parse_scanned_layout`
  - *Tier 2 Boundaries*: `test_pdf_empty_pages`, `test_pdf_corrupt`, `test_pdf_encrypted`, `test_pdf_image_only`, `test_pdf_huge_file`
- [x] **Notion Mocking** (10 tests)
  - *Tier 1 Coverage*: `test_notion_parse_url`, `test_notion_parse_id`, `test_notion_block_hierarchy`, `test_notion_rich_text`, `test_notion_mock_auth`
  - *Tier 2 Boundaries*: `test_notion_missing_key`, `test_notion_invalid_key`, `test_notion_page_not_found`, `test_notion_rate_limit_429`, `test_notion_empty_page`
- [x] **Antigravity CLI Invocation** (10 tests)
  - *Tier 1 Coverage*: `test_cli_invocation_success`, `test_cli_stdout_passthrough`, `test_cli_stderr_passthrough`, `test_cli_exit_code_propagation`, `test_cli_path_resolution`
  - *Tier 2 Boundaries*: `test_cli_missing_binary`, `test_cli_hang`, `test_cli_shell_injection`, `test_cli_huge_args`, `test_cli_killed`

---

## 4. Test Catalog

### Tier 3: Cross-Feature Combinations (5 tests)
- `test_docker_gitconfig_ssh_integration`: Verifies container git commands use both the mounted Git credentials and SSH keys to perform a clone/push operation against a mock SSH remote.
- `test_txt_to_cli_pipeline`: Mounts a `.txt` file into the container, runs `run_agent.py`, and verifies that the parsed text is passed verbatim to the mock `agy` CLI.
- `test_pdf_to_cli_pipeline`: Mounts a `.pdf` file into the container, runs `run_agent.py`, and verifies that the extracted text is passed verbatim to the mock `agy` CLI.
- `test_notion_to_cli_pipeline`: Provides a Notion URL and mock API key, retrieves the page text, and verifies it is passed directly to the mock `agy` CLI.
- `test_cli_gemini_config_interaction`: Runs `run_agent.py` to invoke `agy` inside the container, and verifies that `agy` successfully writes history data to the mounted `/root/.gemini/antigravity-cli` directory.

### Tier 4: Real-world Workloads (5 tests)
- `test_scenario_host_driven_autopilot` (Scenario 1): Host-driven task autopilot. Simulates a developer writing a prompt to a local file, running the agent to process it, invoking the mock `agy` CLI, and generating a FastAPI auth service file `auth.py`.
- `test_scenario_secure_autonomous_release` (Scenario 2): Secure autonomous code release. Verifies Git identity mount inside the container and git commits.
- `test_scenario_multipage_pdf_code_gen` (Scenario 3): Multi-page specification code generator. Extracts schema details from a mock PDF file to feed the agent, creating SQLAlchemy models.
- `test_scenario_notion_ticket_completion_cycle` (Scenario 4): Notion ticket completion cycle. Simulates downloading a task specification from a Notion card page, invoking `agy` to generate code, and checking/updating ticket status via mock API.
- `test_scenario_persistent_context` (Scenario 5): Persistent agent context across container lifecycle. Simulates saving session history/state files to the persistent volume mount and verifying its retrieval after container reboots.
