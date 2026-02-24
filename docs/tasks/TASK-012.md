# Task 012: Event timeline and run audit trail UI

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Add observable run timeline and event audit trail in API and UI.

## Non-goals

- Full production observability stack (external logs/tracing backends).
- Real-time streaming transport (SSE/WebSocket).

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add workflow run entities and lifecycle endpoints (`create/get/list/pause/resume/abort`).
- Add event model and query endpoint with run/task filtering.
- Persist key lifecycle events for run/task/approval actions.
- Add UI section to create runs, inspect run status, and inspect timeline events.

## Acceptance criteria

- [x] API supports run CRUD-like lifecycle needed for monitoring.
- [x] API exposes event timeline endpoint filterable by run/task.
- [x] UI can view run list/status and timeline events.
- [x] Tests cover run lifecycle and event timeline behavior.

## Implementation notes

Use in-memory event store for MVP with stable ordering by event id.

## Test plan

- [x] API tests for run lifecycle and event filtering.
- [x] UI build validation after timeline components are added.

## Risks and mitigations

- Risk: event volume growth in memory store.
- Mitigation: query `limit` and keep MVP storage ephemeral.

## Result

Implemented:
- Added workflow run lifecycle endpoints and in-memory run model:
  - `POST /workflow-runs`
  - `GET /workflow-runs`
  - `GET /workflow-runs/{run_id}`
  - `POST /workflow-runs/{run_id}/pause`
  - `POST /workflow-runs/{run_id}/resume`
  - `POST /workflow-runs/{run_id}/abort`
- Added event timeline endpoint with filters:
  - `GET /events?run_id=<id>&task_id=<id>&limit=<n>`
- Implemented event emission across lifecycle:
  - run created/paused/resumed/aborted
  - task created/dispatched
  - approval pending/approved/rejected
  - lock release
  - dispatch blocked by approval
- Added UI section `Workflow Runs and Timeline` for:
  - creating runs
  - controlling run status
  - viewing selected run and event timeline
- Extended shared contracts with `WorkflowRunRead` and `EventRead` types.

Verification:
- `apps/api`: `./.venv/bin/pytest -q` -> `31 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `4 passed`
- `apps/ui`: `npm run build` succeeded

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
