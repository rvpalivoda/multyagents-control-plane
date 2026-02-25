# Implementation Plan (MVP -> v1)

## Phase 0: Foundation (2-3 days)

- Initialize mono-repo structure:
  - `apps/ui`
  - `apps/api`
  - `apps/telegram-bot`
  - `apps/host-runner`
  - `infra/compose`
- Use Python-only backend baseline for v0.1 (`api`, `telegram-bot`, `host-runner`).
- Add `docker-compose` for UI/API/Postgres/Redis/Bot.
- Add shared schema package for DTOs/contracts.

## Phase 1: Core domain (3-4 days)

- Implement project registry and role CRUD.
- Implement workflow template CRUD (DAG steps + dependencies).
- Persist runs/tasks/events/artifacts.
- Add basic UI pages for projects/roles/workflows.

## Phase 2: Execution pipeline (4-5 days)

- Queue-based task scheduling in API.
- Runner protocol (submit/cancel/status/log stream).
- Implement two modes first:
  - `no-workspace`
  - `shared-workspace`
- Add task retries/timeouts.
- Add Context7 role/task policy resolution and runner payload fields.

## Phase 3: Human-in-the-loop (2-3 days)

- Approval entities and blocking states.
- Telegram commands:
  - run/status/pause/resume/approve/abort
- Notifications on failure/block/approval required.

## Phase 4: Git and isolation (4-5 days)

- `isolated-worktree` mode.
- Branch/worktree lifecycle manager.
- Reviewer gate before merge action.
- Conflict/failure handling and rollback policy.

## Phase 5: Hardening (3-4 days)

- Observability dashboards (status and queue depth).
- Audit timeline for run/task decisions.
- Unified quality-gate summaries for code/content workflows.
- Integration tests for key workflows.
- Documentation and operator runbook.

## Exit criteria for MVP

- UI can fully configure project, role, workflow.
- End-to-end run works with local host codex invocation.
- Telegram approval gate can pause and resume execution.
- At least one coding workflow and one text workflow validated.
