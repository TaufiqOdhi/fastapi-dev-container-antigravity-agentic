# Project Plan — FastAPI Dev Container with Antigravity Agentic Runner

## Objective
Establish a containerized FastAPI development environment integrated with the Antigravity CLI and a text-extracting runner script, persisting source files, Git credentials, and agent history through Docker volume mounts, verified by dual-track E2E testing and white-box coverage hardening.

## Orchestration Strategy
We employ the **Project Pattern** consisting of two parallel tracks:
1. **E2E Testing Track**: Designs independent, opaque-box tests based on requirements across 4 tiers.
2. **Implementation Track**: Implements features across milestones, ending with a milestone to pass all E2E tests and perform white-box adversarial coverage hardening (Tier 5).

## Milestones & Work Partitioning

### Track 1: E2E Testing Track
- **M1: Test Infrastructure Design & Implementation**: Setup test harness, runner script, and verification helper scripts inside the workspace.
- **M2: Test Case Implementation (Tiers 1-4)**:
  - **Tier 1 (Feature Coverage)**: At least 5 test cases per feature (Docker Env, Runner script parsing txt/pdf/mock Notion, CLI invocation).
  - **Tier 2 (Boundary/Corner Cases)**: At least 5 boundary cases per feature (empty file, invalid paths, missing mock keys, extreme inputs).
  - **Tier 3 (Cross-Feature Combinations)**: Interaction testing.
  - **Tier 4 (Real-world Workloads)**: End-to-end integration workflows.
- **M3: Publish TEST_READY.md**: Finalize and summarize the test suite.

### Track 2: Implementation Track
- **M4: Docker & FastAPI Setup (R1)**: Create Dockerfile and docker-compose.yml with Python 3.14+, FastAPI, and standard tools.
- **M5: Volume Mounts & Host Integration (R3)**: Map Git config/SSH keys and `.gemini/antigravity-cli` safely to allow persistency and permissions.
- **M6: Agentic Runner & Antigravity CLI (R2)**: Install `agy` CLI, write `run_agent.py` to support txt, pdf, and mock Notion parsing, and execute the CLI.
- **M7: E2E Integration and Hardening (Phase 1 & 2)**:
  - Phase 1: Pass 100% of the E2E tests published by the E2E Testing Track.
  - Phase 2: White-box coverage hardening (Tier 5) using Challenger-led adversarial testing.

## Verification & Validation Plan
- **Verification**: Each subagent runs unit tests and checks log output.
- **Challengers**: Run adversarial stress testing on integration points.
- **Forensic Auditor**: Validate that there are no hardcoded test results, facade implementations, or other integrity violations.
