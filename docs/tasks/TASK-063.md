# Task 063: Contract Regression Suite (Summary/Gates/Timeline)

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Укрепить совместимость API контрактов для новых полей и рабочих потоков.

## Scope

- Regression tests for execution summary fields.
- Regression tests for quality gates + timeline + triage composition.
- Backward compatibility checks for older clients.

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной локальной работы.
- [x] Виден прозрачный результат/процесс в UI/API/docs.
- [x] Покрыто targeted tests и smoke.

## Test plan

- [x] API tests + локальный smoke-run.

## Result

- Added `apps/api/tests/test_api_contract_regression.py` to verify additive compatibility for run/summary contracts (gates/timeline/triage fields).
- Validation: `.venv/bin/pytest -q tests/test_api_contract_regression.py tests/test_api_partial_rerun.py tests/test_api_control_loop.py` -> passed (7).
- Commits: `<final-sha>`
