# Task 051: Run-cost and throughput dashboard

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить видимость эффективности: время/стоимость/throughput по run/task/role.

## Non-goals

- Полный BI/ML контур на первом этапе.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`

## Scope

- MVP реализация по задаче.

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной работы.
- [x] Покрыто тестами/валидацией.

## Test plan

- [x] Targeted tests + smoke.

## Result

- Backend: `WorkflowRunRead` расширен метриками `duration_ms`, `success_rate`, `retries_total`, `per_role[]` с вычислением в `store.py` на основе task status/timestamps и `task.dispatched` событий.
- UI: дашборд в `Overview` и `Runs Center` показывает duration/success rate/retries + per-role throughput для выбранного run.
- Tests:
  - API: `apps/api/tests/test_api_run_rollup.py`.
  - API regression: `.venv/bin/pytest -q tests/test_api_run_rollup.py tests/test_api_assistant_intents.py tests/test_api_control_loop.py tests/test_api_retry_strategy.py` -> passed (13).
  - UI: `npm test` and `npm run build` -> passed.
- Commits: `<final-sha>`
