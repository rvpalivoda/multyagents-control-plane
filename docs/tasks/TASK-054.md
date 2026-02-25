# Task 054: Assistant Control Loop (Plan->Spawn->Aggregate)

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать контур, где ассистент одной командой запускает комплексную работу: декомпозиция -> параллельные агенты -> агрегация результата -> отчёт.

## Scope

- API contract для orchestration intent.
- Структурированный execution summary для чата.
- Safety hooks (approval-required stages).

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#6-inter-agent-contract`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Acceptance criteria

- [x] Один запрос ассистента запускает мультишаговый план.
- [x] Есть machine-readable итог с результатами всех веток.
- [x] Поддержаны ошибки/partial completion.

## Implementation notes

- Added assistant control-loop API endpoint:
  - `POST /workflow-runs/{run_id}/control-loop`
  - executes `plan -> spawn -> aggregate` in one call over existing primitives (`dispatch_task`, runner submit, `apply_runner_submission`)
- Added run-level execution summary endpoint:
  - `GET /workflow-runs/{run_id}/execution-summary`
  - returns machine-readable run/task state, status counts, next dispatch plan, and handoff/artifact rollups.
- Added store helpers:
  - `plan_workflow_run_dispatch`
  - `get_workflow_run_execution_summary`
  - explicit blocked reasons: paused/aborted run, dependencies, missing required handoff artifacts, approval-required, dispatch-limit.
- Added control-loop API tests:
  - `apps/api/tests/test_api_control_loop.py`
  - scenarios: parallel plan/spawn with partial failure and approval-gated stages.

## Test plan

- [x] Added API tests + one end-to-end orchestrated scenario in `apps/api/tests/test_api_control_loop.py`.
- [x] Execute targeted pytest in local environment.

## Result

- Verification evidence:
  - `cd apps/api && python3 -m py_compile src/multyagents_api/schemas.py src/multyagents_api/store.py src/multyagents_api/main.py tests/test_api_control_loop.py` -> passed.
  - `apps/api`: `.venv/bin/pytest -q tests/test_api_control_loop.py` -> passed.
- Commits:
  - `70aff46`
