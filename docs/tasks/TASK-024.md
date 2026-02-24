# Task 024: Add workflow DAG run expansion and dispatch-ready endpoint

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Make workflow runs executable in dependency order by expanding workflow template steps into run tasks and dispatching only ready tasks.

## Non-goals

- Full parallel scheduler daemon.
- Automatic retries/backoff strategy for failed steps.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-workflow-builder-from-ui`
- Architecture: `docs/ARCHITECTURE.md#3-run-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- On run creation from `workflow_template_id`, auto-create one task per template step.
- Persist per-run task dependency mapping derived from step DAG.
- Add endpoint `POST /workflow-runs/{run_id}/dispatch-ready`.
- Dispatch first ready task where all dependencies are in `success`.
- Return no-op response when no task is ready.
- Add API tests for template expansion and sequential dependency dispatch.
- Add UI action to trigger `dispatch-ready`.

## Acceptance criteria

- [x] Workflow run from template creates run tasks automatically.
- [x] Dependency order is respected during dispatch-ready.
- [x] Dispatch-ready returns explicit result (`dispatched` true/false).
- [x] API tests validate ordered dispatch behavior.

## Implementation notes

Treat dependency completion condition as strict `success` for MVP.

## Test plan

- [x] API tests for template expansion and DAG-ready dispatch.
- [x] Full regressions and UI build.

## Risks and mitigations

- Risk: deadlock when dependencies fail or are canceled.
- Mitigation: explicit no-ready result and event trail for operator intervention.

## Result

Implemented DAG-aware workflow run execution primitives:

- Workflow run creation now auto-expands template steps into tasks when:
  - `workflow_template_id` is provided
  - `task_ids` is empty
- Added internal per-run dependency mapping (`task_id -> dependency task_ids`).
- Added API endpoint:
  - `POST /workflow-runs/{run_id}/dispatch-ready`
  - Returns explicit result:
    - `dispatched=true` with task id and dispatch payload
    - `dispatched=false` with reason (`dependencies not satisfied` / `no ready tasks`)
- Dispatch-ready only selects tasks where all dependencies have `success`.
- Added UI control:
  - `Dispatch ready task` button in Workflow Runs section
  - stores and shows dispatch-ready response payload
- Added API integration test:
  - `apps/api/tests/test_api_workflow_dispatch_ready.py`
  - validates template expansion, blocked second step until dependency success, then second dispatch.

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `41 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `8 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/ui`: `npm run build` successful
