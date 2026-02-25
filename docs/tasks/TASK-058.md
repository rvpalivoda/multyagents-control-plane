# Task 058: Process Transparency Timeline

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать прозрачный timeline процесса для оператора: кто (owner) ведет ветку, на каком этапе (stage) находится задача, что активно, что заблокировано и что завершено.

## Non-goals

- Изменение базовой модели workflow/task статусов.
- Переработка существующего event timeline контракта (`/events`).
- Новый режим исполнения или изменение runner протокола.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#6-inter-agent-contract`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Additive API fields in run execution summary:
  - run-level `progress_percent`
  - `branch_status_cards` (`active`/`blocked`/`done`)
  - structured `timeline[]` entries (`branch`, `owner_role_id`, `stage`, `stage_id`, `stage_state`, `progress_percent`, blockers)
- UI wiring to fetch `GET /workflow-runs/{run_id}/execution-summary` for selected run.
- Runs UI updates:
  - clear Active/Blocked/Done cards
  - process transparency table with branch/owner/stage/state/progress
  - selected run progress visibility.
- Targeted API and UI test updates.

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной работы (phase 1: progress/cards).
- [x] Видно прогресс/результаты в UI и API (progress/cards).
- [x] Полное покрытие transparency timeline тестами.

## Implementation notes

- Kept compatibility by adding only new optional/defaulted response fields to `WorkflowRunExecutionSummary`.
- Derived branch/stage context from workflow template step graph when available, with safe fallback for manual runs.
- Blocked state reasons reuse existing dispatch constraints (dependencies, required handoff artifacts, approval) and terminal failure statuses.

## Test plan

- [x] UI smoke tests (`vitest`): runs transparency rendering and existing workflow builder flow.
- [x] UI build (`vite build`).
- [x] API syntax checks (`py_compile`) for touched Python files.
- [x] API runtime tests added/updated (execution summary assertions).

## Risks and mitigations

- Risk: timeline branch labels for non-template runs can be less semantic.
- Mitigation: fallback naming (`task-<id>`) is explicit and deterministic.
- Risk: API runtime tests could not be executed in this sandbox (no network to install FastAPI/pytest deps).
- Mitigation: added assertions in API tests, validated Python syntax with `py_compile`, and documented environment limitation.

## Result

- Delivered:
  - execution summary timeline[] with branch/owner/stage/stage_state/progress/blockers;
  - run-level progress cards (active/blocked/done + progress_percent) wired to execution-summary endpoint;
  - Runs Center transparency timeline table bound to execution summary.
- Verification:
  - `apps/api`: `.venv/bin/pytest -q tests/test_api_control_loop.py tests/test_api_partial_rerun.py tests/test_api_quality_gates.py tests/test_api_run_rollup.py tests/test_api_retry_strategy.py` -> passed (14).
  - `apps/ui`: `npm run build` -> passed.
- Commits: `<final-sha>`
