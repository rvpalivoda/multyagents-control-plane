# Task 043: Workflow Validation UX (inline errors + cycle checks)

## Metadata

- Status: `todo`
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

- [ ] Пользователь видит ошибки до отправки формы.
- [ ] Нельзя отправить workflow с циклом.
- [ ] Тексты ошибок понятны оператору.

## Implementation notes

Выделить чистые функции валидации для unit-тестов.

## Test plan

- [ ] Unit тесты на валидацию DAG.
- [ ] Ручной smoke: invalid dependency / cycle.

## Risks and mitigations

- Risk: Слишком строгая валидация ломает старые сценарии.
- Mitigation: Согласовать с backend правилами из `workflow_validation.py`.

## Result

- Commits: `<sha1>`
