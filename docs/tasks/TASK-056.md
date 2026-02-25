# Task 056: Unified Quality Gates (Code + Content)

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать единый механизм quality gates для code/content workflow, чтобы переходы между шагами были прозрачными и контролируемыми.

## Non-goals

- Изменение текущего dispatch scheduler/state machine.
- Жесткое блокирование исполнения по quality gates (в этой задаче только оценка и прозрачность).
- Перепроектирование runner protocol.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Additive gate policy model:
  - `required_checks[]`
  - check `severity` (`blocker` / `warn`)
  - `required` flag per check
- Task-level gate evaluation (human-readable + machine-readable).
- Run-level aggregate gate summary.
- API exposure in existing run/task read models (backward-compatible additive fields).
- UI rendering in run view and task view.
- Targeted backend/UI tests.
- Contracts update (`packages/contracts` TS + JSON schema).

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной работы.
- [x] Видно прогресс/результаты в UI и API.
- [x] Покрыто targeted tests.

## Implementation notes

- Added quality gate policy/evaluation models in API schemas:
  - `QualityGatePolicy`
  - `QualityGateSummary` (task-level)
  - `QualityGateRunSummary` (run-level)
- Added default policy (`task-status` blocker check) for backward-compatible existing tasks/steps without explicit policy.
- Extended workflow step schema with `quality_gate_policy`; propagated to generated tasks in workflow runs.
- Implemented gate evaluators in store:
  - `task-status`
  - `approval-status`
  - `handoff-present`
  - `required-artifacts-present`
- Gate summary is now available in:
  - `TaskRead`
  - `WorkflowRunRead`
  - `WorkflowRunExecutionSummary.tasks[]`
- Updated UI:
  - Runs Center table/details now show gate status and summary.
  - Tasks view now shows gate status column and selected-task gate details.
- Kept existing contracts backward-compatible by adding optional fields in shared TS contracts and non-required properties in JSON schema.

## Test plan

- [x] Python syntax checks for touched backend files:
  - `python3 -m py_compile apps/api/src/multyagents_api/schemas.py apps/api/src/multyagents_api/store.py apps/api/tests/test_api_quality_gates.py`
- [x] JSON schema validation:
  - `python3 -m json.tool packages/contracts/v1/context7.schema.json`
- [x] Targeted tests added:
  - `apps/api/tests/test_api_quality_gates.py`
  - `apps/ui/src/components/RunsCenterSection.test.tsx`
- [x] Full targeted API/UI test/build commands executed in local environment.

## Risks and mitigations

- Risk: Existing clients may not expect new fields.
- Mitigation: Additive-only contract changes; old fields preserved; TS fields marked optional.

- Risk: Incomplete runtime verification due missing local test/build dependencies in this sandbox.
- Mitigation: Added focused tests + compile/schema checks; recorded exact command failures for follow-up in a fully provisioned dev env.

## Result

- Implemented unified quality-gate policy/evaluation across task/run API surfaces and UI run/task views.
- Added targeted API/UI tests for new behavior.
- Updated product/architecture/implementation docs to reflect quality gate capability.
- Verification evidence:
  - `python3 -m py_compile ...` -> passed.
  - `python3 -m json.tool packages/contracts/v1/context7.schema.json` -> passed.
- `apps/api`: `.venv/bin/pytest -q tests/test_api_quality_gates.py tests/test_api_assistant_intents.py tests/test_api_control_loop.py tests/test_api_retry_strategy.py tests/test_api_run_rollup.py` -> passed (15).
- `apps/ui`: `npm test` -> passed (13); `npm run build` -> passed.
- Commits: `<final-sha>`.
