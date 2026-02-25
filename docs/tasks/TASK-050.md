# Task 050: Assistant-Facing Orchestration API (Chat-Friendly)

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить удобный API слой для работы ассистента: создать план -> запустить N агентов -> получить агрегированный статус/результат.

## Non-goals

- Перестройка базового runner protocol или workflow CRUD контрактов.
- Реализация полного background scheduler/cost analytics (covered by other tasks).

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Assistant intent endpoints:
  - `POST /assistant/intents/plan`
  - `POST /assistant/intents/start`
  - `POST /assistant/intents/status`
  - `POST /assistant/intents/report`
- Machine-readable summary payload for plan/start/status/report responses.
- Approval-aware start behavior (do not bypass gate; return blocked task IDs).
- Workflow-run step override contract for assistant-driven starts.

## Acceptance criteria

- [x] Ассистент может запускать мультиагентный pipeline одной командой (`/assistant/intents/start` with initial ready dispatch).
- [x] Ассистент получает структурированный итог без ручного парсинга логов (machine summary + report payload).
- [x] Сохранён контроль через approval policy (pending approvals are reported as blockers, not auto-dispatched).

## Implementation notes

- Added assistant intent DTOs and machine summary schema in `apps/api/src/multyagents_api/schemas.py`.
- Extended workflow run creation with optional `step_task_overrides` for per-step execution/approval settings.
- Added store-level assistant services in `apps/api/src/multyagents_api/store.py`:
  - `plan_assistant_intent`
  - `start_assistant_intent`
  - `status_assistant_intent`
  - `report_assistant_intent`
- Added new API routes in `apps/api/src/multyagents_api/main.py`.
- Updated API docs in `apps/api/README.md`.

## Test plan

- [x] API contract tests added in `apps/api/tests/test_api_assistant_intents.py`.
- [x] Execute targeted pytest in local environment.
- [x] Syntax validation via `python3 -m py_compile` for touched modules.

## Result

- Delivered:
  - assistant-facing intent API for plan/start/status/report;
  - machine-readable orchestration summary for chat automation;
  - approval-aware initial dispatch behavior;
  - assistant intent API tests and docs updates.
- Verification:
  - `apps/api`: `.venv/bin/pytest -q tests/test_api_assistant_intents.py` -> passed.
- Commits: `<final-sha>`
