# Scope: Milestone 3 — Volume Mounts

## Architecture
Orchestrate local volume mounts and host integration for the FastAPI development container using Docker Compose.
- **docker-compose.yml**:
  - Map workspace directory (`/workspace`) to the host project directory.
  - Map host SSH keys (`~/.ssh`) to `/root/.ssh` (read-only/writable as needed).
  - Map host Git configuration (`~/.gitconfig`) to `/root/.gitconfig` (read-only).
  - Map host Antigravity CLI config/data directory (`~/.gemini/antigravity-cli`) to `/root/.gemini/antigravity-cli`.

## Milestones
| # | Name | Scope | Dependencies | Status | Conv ID |
|---|------|-------|--------------|--------|---------|
| 3.1 | Compose Configuration | Create docker-compose.yml and verify mounts | None | PLANNED | TBD |

## Interface Contracts
- Container runs successfully via `docker compose up -d`.
- SSH keys, gitconfig, and antigravity-cli directories are correctly mounted and accessible inside the container.
