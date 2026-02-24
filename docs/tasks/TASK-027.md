# Task 027: Auto-update workflow run status from task lifecycle outcomes

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Automatically roll up run status based on task execution outcomes to remove manual status drift.

## Non-goals

- Rich state machine with retries and partial success.
- Cross-run aggregation analytics.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Recompute run status when task submission/result statuses change.
- Mark run `success` when all run tasks are `success`.
- Mark run `failed` when any run task is terminal failure (`failed`, `canceled`, `submit-failed`).
- Emit events for auto status transitions.
- Add API tests for success and failure rollup.

## Acceptance criteria

- [x] Run status auto-transitions to `success` when all tasks succeed.
- [x] Run status auto-transitions to `failed` on task failure/cancel/submit-failed.
- [x] Existing manual abort semantics stay authoritative.
- [x] API tests cover rollup behavior.

## Implementation notes

Skip rollup updates when run is already `aborted`.

## Test plan

- [x] Add API tests for run success and failure rollup.
- [x] Full regressions and UI build.

## Risks and mitigations

- Risk: noisy repeated status events.
- Mitigation: emit event only when status actually changes.

## Result

Implemented automatic run status rollup from task lifecycle:

- Added run status recomputation on task lifecycle updates from:
  - dispatch transition
  - runner submit outcome
  - runner status callbacks
  - runner cancel propagation
- Rollup logic:
  - `success`: all run tasks are `success`
  - `failed`: any run task is `failed`, `canceled`, or `submit-failed`
  - `running`: any run task is in active status (`dispatched`, `queued`, `running`, `cancel-requested`)
- Preserved manual `aborted` authority:
  - no auto-rollup changes applied once run is `aborted`.
- Added run events for automatic transitions:
  - `workflow_run.running`
  - `workflow_run.succeeded`
  - `workflow_run.failed`

Tests added:

- `apps/api/tests/test_api_run_rollup.py`
  - success rollup when all tasks reach `success`
  - failure rollup when any task reaches `failed`

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `45 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `12 passed`
- `apps/ui`: `npm run build` successful

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
