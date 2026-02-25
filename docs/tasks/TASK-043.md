# Task 043: Workflow Validation UX (inline errors + cycle checks)

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить понятные inline-ошибки в конструкторе workflow и раннее предотвращение невалидных DAG.

## Non-goals

- Серверная замена валидатора.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Валидации: duplicate step id, пустые поля, несуществующие зависимости, self-dependency.
- Проверка циклов в DAG до submit.
- Ошибки на уровне карточки и summary-блок над формой.

## Acceptance criteria

- [x] Пользователь видит ошибки до отправки формы.
- [x] Нельзя отправить workflow с циклом.
- [x] Тексты ошибок понятны оператору.

## Implementation notes

Выделены и переиспользованы функции валидации для quick/json режимов.

## Test plan

- [x] Unit тесты на валидацию DAG.
- [x] Ручной smoke: invalid dependency / cycle.

## Risks and mitigations

- Risk: Слишком строгая валидация ломает старые сценарии.
- Mitigation: Согласовано с backend правилами из `workflow_validation.py`.

## Result

- Добавлена единая пред-валидация DAG для Quick и Raw JSON перед submit.
- Добавлен validation summary блок.
- Добавлены card-level ошибки (визуальная подсветка + сообщения в карточке).

Execution evidence:
- `cd apps/ui && npm test` -> passed (8 tests)
- `cd apps/ui && npm run build` -> passed

Commits:
- `<final-sha>`
