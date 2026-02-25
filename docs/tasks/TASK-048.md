# Task 048: Shared Handoff Board for Agent-to-Agent Context

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать явный handoff-board между агентами: что сделано, что передать дальше, какие артефакты обязательны для следующего шага.

## Non-goals

- Новый язык workflow или изменение DAG модели.
- Изменение runner executor логики (shell/codex/docker) вне handoff payload в submit контракте.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#6-inter-agent-contract`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Структурированный handoff payload в task completion.
- UI панель handoff в run details.
- Валидация обязательных артефактов перед dispatch следующего шага.

## Acceptance criteria

- [x] Следующий шаг получает структурированный handoff без ручного копипаста.
- [x] Отсутствие обязательного handoff блокирует dispatch с понятной ошибкой.
- [x] Handoff отражается в event timeline.

## Implementation notes

- API schemas extended with structured handoff models:
  - `TaskHandoffPayload`
  - `TaskHandoffArtifactRef`
  - `TaskHandoffRead`
- Runner status callback (`POST /runner/tasks/{task_id}/status`) now accepts optional `handoff` on terminal statuses.
- Handoff payload is persisted in API state snapshot and exposed via:
  - `GET /handoffs`
  - `GET /tasks/{task_id}/handoff`
  - `TaskAudit.handoff`
- Timeline now includes explicit `task.handoff_published` events.
- Dispatch gating for `required_artifacts` now requires artifacts to be explicitly marked `is_required=true` in upstream handoff payload.
- `dispatch-ready` blocking reason was clarified to:
  - `required handoff artifacts missing`
- Dispatch payload includes resolved dependency handoff context (`runner_payload.handoff_context`).
- Runs Center UI now shows a dedicated handoff board panel in run details (summary, next actions, open questions, required artifacts).

## Test plan

- [x] API tests: handoff schema persistence + endpoint visibility + timeline event.
- [x] API tests: dispatch-ready blocking when required artifacts are not marked in handoff.
- [x] API/integration tests: dispatch-ready success when required handoff artifacts are published.

## Result

- Delivered:
  - structured task-completion handoff contract and persistence;
  - handoff-aware dispatch blocking for dependent steps;
  - run-details handoff board in UI;
  - API tests for schema and blocking behavior.
- Verification evidence:
  - `cd apps/api && python3 -m py_compile src/multyagents_api/*.py tests/test_api_workflow_dispatch_ready.py tests/test_api_events_artifacts.py tests/test_integration_workflows.py` -> passed.
  - `cd apps/api && python3 -m pytest ...` -> failed (`No module named pytest` in environment).
  - `cd apps/ui && npm ci` -> failed during `esbuild` postinstall (`spawnSync ... EPERM`).
  - `cd apps/ui && npm test` / `npm run build` -> failed because toolchain install did not complete (`vitest` / `vite` not found).
- Commits:
  - `<pending: commit blocked in sandbox (index.lock permission denied)>`

## Result

- Delivered:
  - structured task-completion handoff contract and persistence;
  - handoff-aware dispatch blocking for dependent steps;
  - run-details handoff board in UI;
  - API tests for schema and blocking behavior.

Verification evidence:
- `apps/api`: `.venv/bin/pytest -q tests/test_api_events_artifacts.py tests/test_api_workflow_dispatch_ready.py tests/test_integration_workflows.py tests/test_api_cancel.py tests/test_api_context7.py tests/test_api_runner_status.py` -> passed (31).
- `apps/telegram-bot`: `.venv/bin/pytest -q tests/test_bot_api.py` -> passed (13).
- `apps/ui`: `npm test` -> passed (10), `npm run build` -> passed.

Commits:
- `<final-sha>`
