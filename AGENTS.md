# AGENTS.md

This repository builds a universal multi-agent orchestration platform.

## Goal

Create a control plane that can run many Codex-based agents for different task types:
- software development
- text writing
- research and analysis
- mixed workflows (code + docs + review)

The system must run in Docker, while invoking local host `codex` CLI through a host runner.

## Source of truth

Specification-first process is mandatory:
1. `docs/PRODUCT_SPEC.md` is product source of truth.
2. `docs/ARCHITECTURE.md` is technical source of truth.
3. `docs/IMPLEMENTATION_PLAN.md` maps work to milestones.
4. `docs/DEVELOPMENT_PROCESS.md` defines task and delivery workflow.
5. Code/tasks must reference spec sections.

Do not implement features that are not described in the spec/architecture docs.

## Core constraints

- Multi-project support is required.
- Agent roles are created and configured from UI.
- Workflows are configurable from UI (DAG, retries, approvals, policies).
- Agents can run with or without workspace:
  - `no-workspace` (text/research tasks)
  - `shared-workspace`
  - `isolated-worktree`
  - `docker-sandbox`
- Inter-agent communication must use structured events/artifacts.
- Human-in-the-loop via Telegram is required.

## Runtime model

- Docker services: UI, API, DB, queue, bot.
- Host service: runner that invokes local `codex` CLI.
- API never executes `codex` directly inside containers.

## Tech baseline (v0.1)

- Language baseline is Python-only for backend services.
- `api`, `telegram-bot`, and `host-runner` are Python services.
- Frontend remains React + TypeScript.

## Task governance

- Backlog is tracked in `docs/BACKLOG.md`.
- Each active task must have a file under `docs/tasks/` from template.
- Task state transitions must follow `docs/DEVELOPMENT_PROCESS.md`.
- Every task moved to `review` or `done` must have at least one git commit.
- Task `Result` must include commit SHA evidence before `done`.
- Non-trivial architecture changes require ADR entry in `docs/adr/`.

## Project skills

- Project-specific skills are versioned under `skills/`.
- Skill list and intent are documented in `docs/SKILLS_CATALOG.md`.

## Engineering rules

- Keep interfaces explicit: versioned schemas for role/workflow/task/artifact.
- Prefer backward-compatible changes.
- Every workflow behavior must be testable via integration tests.
- Add migrations for data model changes.
- Record key tradeoffs as ADR entries under `docs/adr/`.

## Definition of done

A feature is done only if:
1. Spec/architecture updated.
2. API/UI/runner behavior implemented.
3. Tests added (unit or integration as applicable).
4. Observability present (logs/events/status transitions).
5. User-facing docs updated.
