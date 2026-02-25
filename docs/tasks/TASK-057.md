# Task 057: Partial Re-run Engine (Failed Branches Only)

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Позволить перезапускать только провалившиеся ветки/шаги workflow без полного перезапуска run.

## Non-goals

- Полный рестарт run с пересозданием всех задач.
- Ломающее изменение существующих `WorkflowRunRead`/`TaskRead` контрактов.
- Изменение runner transport или протокола callback.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- API endpoint partial rerun by task_ids/step_ids.
- UI controls for selective rerun with safety confirmations.
- Audit trail: who reran what and why.

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной работы.
- [x] Видно прогресс/результаты в UI и API.
- [x] Покрыто targeted tests.

## Implementation notes

- Added `POST /workflow-runs/{run_id}/partial-rerun` with request selection by `task_ids` and/or `step_ids`.
- Added safety validation in API store:
  - run must exist and not be paused/aborted,
  - run must have no active tasks,
  - selected items must belong to run,
  - only failed terminal tasks (`failed` / `canceled` / `submit-failed`) are rerunnable,
  - `step_ids` are allowed only for template-based runs and resolved to run tasks.
- Added partial rerun engine behavior:
  - reset only selected failed tasks to `created`,
  - preserve other branches untouched,
  - recompute run as `running`,
  - optional immediate dispatch of selected ready tasks.
- Added audit + events for rerun traceability:
  - `TaskAudit` fields: `rerun_count`, `last_rerun_by`, `last_rerun_reason`, `last_rerun_at`,
  - events: `workflow_run.partial_rerun_requested`, `task.partial_rerun_reset`.
- Added Runs Center controls for selective rerun:
  - checkbox selection of failed tasks,
  - optional step IDs input,
  - required `requested_by` and `reason`,
  - confirmation prompt before submit.
- Kept run/task contracts backward-compatible by using additive optional audit fields and a new endpoint.

## Test plan

- [x] API tests added: `apps/api/tests/test_api_partial_rerun.py`.
- [x] UI test updated: `apps/ui/src/components/RunsCenterSection.test.tsx`.
- [x] Static checks:
  - `python3 -m py_compile apps/api/src/multyagents_api/schemas.py apps/api/src/multyagents_api/store.py apps/api/src/multyagents_api/main.py apps/api/tests/test_api_partial_rerun.py`
  - `python3 -m json.tool packages/contracts/v1/context7.schema.json`
  - `apps/ui`: `npm run build` (passed).
- [x] Runtime tests executed in local environment for API (`test_api_partial_rerun` + regressions); UI build passed.
- [ ] Stabilize UI vitest exit behavior for full suite in this environment (currently hangs post-run).

## Result

- Delivered partial rerun engine for failed branches/tasks with API, store safety checks, rerun audit trail, and Runs Center controls.
- Contracts kept backward-compatible (additive changes only).
- Verification:
  - `apps/api`: `.venv/bin/pytest -q tests/test_api_partial_rerun.py tests/test_api_quality_gates.py tests/test_api_run_rollup.py tests/test_api_retry_strategy.py tests/test_api_assistant_intents.py` -> passed (16).
  - `apps/ui`: `npm run build` -> passed.
- Commits: `388d1f0`
