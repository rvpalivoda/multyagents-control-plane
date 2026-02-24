# Task 021: Add runner status callback sync and automatic lock release

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Synchronize task runtime status from host-runner back to API and ensure shared-workspace locks are released automatically on terminal outcomes.

## Non-goals

- Full streaming logs transport between runner and API.
- Workflow-level auto completion based on all task terminal statuses.

## References

- Product spec: `docs/PRODUCT_SPEC.md#6-acceptance-criteria-mvp`
- Architecture: `docs/ARCHITECTURE.md#3-run-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Add API endpoint for runner status callback updates.
- Track task execution state in API task model.
- Update task state on dispatch submit result (success/failure).
- Auto-release shared-workspace locks on terminal callback status.
- Add host-runner callback sender to API on running/terminal transitions.
- Add tests for callback flow and lock release behavior.

## Acceptance criteria

- [x] API supports runner-to-API status callback for task lifecycle updates.
- [x] Task status is visible via task read model.
- [x] Shared workspace locks are auto-released on terminal task statuses.
- [x] Failed runner submit does not leave stale locks.
- [x] API + host-runner tests validate callback lifecycle.

## Implementation notes

Use lightweight callback with optional shared token header for local security.

## Test plan

- [x] Extend API tests for callback, status transitions, and lock cleanup.
- [x] Extend host-runner tests for callback emission.
- [x] Run full regressions and UI build.

## Risks and mitigations

- Risk: callback outages can desync status between runner and API.
- Mitigation: callback is best-effort with explicit event trail; manual lock release endpoint remains available.

## Result

Implemented runner-to-API status synchronization with automatic lock lifecycle handling:

- Added task runtime status model (`created`, `dispatched`, `queued`, `running`, `success`, `failed`, `canceled`, `submit-failed`) and exposed it in `TaskRead`.
- Added API callback endpoint:
  - `POST /runner/tasks/{task_id}/status`
  - optional token check via `API_RUNNER_CALLBACK_TOKEN` and `X-Runner-Token`.
- Added store methods for:
  - runner submission outcome handling (`queued` vs `submit-failed`)
  - callback status updates with event emission
  - automatic shared-workspace lock release on terminal states and submit failure.
- Updated dispatch flow to persist runner submission outcome immediately.
- Extended host-runner submit payload with callback fields and implemented callback emission on `running` and terminal statuses.
- Updated shared contracts (`packages/contracts/ts`, JSON schema), compose envs, and app READMEs.

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `37 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `6 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/ui`: `npm run build` successful
