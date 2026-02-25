# Task 052: Auto-triage failed runs

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Автоматическая классификация падений и предложение next action в UI/Telegram.

## Non-goals

- Полный BI/ML контур на первом этапе.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`

## Scope

- MVP реализация по задаче.
- API: авто-классификация причин падения для task/run.
- UI: отображение triage и suggested next actions в Runs Center.
- Контракты: расширение `TaskRead` и `WorkflowRunRead` triage-полями.

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной работы.
- [x] Покрыто тестами/валидацией.

## Test plan

- [x] Добавлены targeted API tests: `apps/api/tests/test_api_failure_triage.py`.
- [x] Python syntax smoke: `python3 -m compileall apps/api/src/multyagents_api`.
- [x] Прогон API regression: `.venv/bin/pytest -q tests/test_api_failure_triage.py tests/test_api_retry_strategy.py tests/test_api_run_rollup.py`.
- [x] UI regression: `npm test` + `npm run build`.

## Result

- Реализован auto-triage в API для `failed`/`submit-failed`/`canceled` task-статусов с вычислением:
  - `failure_category`
  - `failure_triage_hints`
  - `suggested_next_actions`
- Добавлена агрегация triage на уровне run:
  - `failure_categories`
  - `failure_triage_hints`
  - `suggested_next_actions`
- UI Runs Center дополнен блоком Failure triage:
  - run-level категории/подсказки/next actions
  - task-level triage summary для failed-задач
- Обновлены контракты (`packages/contracts/ts` + JSON schema).
- Обновлены spec/architecture формулировки для triage behavior.

- Commits: `<final-sha>`
