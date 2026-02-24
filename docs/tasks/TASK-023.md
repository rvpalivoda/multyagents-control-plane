# Task 023: Propagate task/run cancel actions to host-runner

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Ensure operator abort/cancel actions are not only metadata changes in API, but actively sent to host-runner task processes.

## Non-goals

- Guaranteed process kill for every external tool type.
- Distributed cancellation across multiple runners.

## References

- Product spec: `docs/PRODUCT_SPEC.md#7-telegram-integration`
- Architecture: `docs/ARCHITECTURE.md#3-run-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-3-human-in-the-loop-2-3-days`

## Scope

- Add runner client cancel call (`POST /tasks/{task_id}/cancel`).
- Add API endpoint `POST /tasks/{task_id}/cancel`.
- On `POST /workflow-runs/{run_id}/abort`, send cancel requests for tasks in run.
- Track cancel request state in task status.
- Add API tests for task cancel and run abort propagation.
- Add UI task cancel action.

## Acceptance criteria

- [x] Task cancel endpoint exists and calls host-runner cancel API.
- [x] Workflow run abort triggers cancel requests for linked tasks.
- [x] Task status reflects cancel requested/canceled lifecycle.
- [x] API tests cover cancel propagation behavior.

## Implementation notes

Use best-effort runner cancel with explicit task events when runner unavailable.

## Test plan

- [x] Extend API tests for task cancel and run abort cancel propagation.
- [x] Run full regressions and UI build.

## Risks and mitigations

- Risk: runner unavailable when cancel requested.
- Mitigation: keep task audit/event trail with cancel failure details for operator retry.

## Result

Implemented cancel propagation from API control actions to host-runner:

- Added runner client cancel operation:
  - `cancel_in_runner(task_id)` -> `POST /tasks/{task_id}/cancel`
- Added API endpoint:
  - `POST /tasks/{task_id}/cancel`
  - Updates task state based on runner cancel response.
- Updated run abort flow:
  - `POST /workflow-runs/{run_id}/abort` now sends cancel request for each task in run.
- Extended task status model with `cancel-requested`.
- Added store handling for cancel submission outcomes:
  - `task.runner_cancel_requested`
  - `task.runner_cancel_failed`
  - immediate `canceled` + lock release when runner returns terminal canceled state.
- UI updates:
  - Added `Cancel task` action in Dispatch section.
  - Added `Refresh task` action to reload current task status.

Tests added:

- `apps/api/tests/test_api_cancel.py`
  - task cancel endpoint propagation
  - run abort cancel fanout for all run tasks

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `40 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `8 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/ui`: `npm run build` successful
