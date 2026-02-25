# Task 053: Template recommendation engine

## Metadata

- Status: `done`
- Priority: `P2`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Рекомендовать лучший workflow template по типу запроса и истории запусков.

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

- Implemented template recommendation endpoint and scoring logic (intent + optional historical success heuristics).
- Added workflow UI recommendation panel with prompt, detected intents, ranked template list, and one-click apply.
- Validation:
  - `apps/api`: `.venv/bin/pytest -q tests/test_api_template_recommendations.py tests/test_api_contract_regression.py tests/test_api_partial_rerun.py` -> passed (9).
  - `apps/ui`: `npm run build` -> passed.
- Commits: `<final-sha>`
