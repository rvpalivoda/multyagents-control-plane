# Task 042: Workflow Builder Quick Create UX

## Metadata

- Status: `in_progress`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать создание workflow удобным для оператора: пошаговый конструктор вместо обязательного ручного JSON.

## Non-goals

- Полный визуальный DAG-редактор с canvas.
- Изменение API контракта workflow step.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Добавить режим `Quick create` в UI для шагов workflow.
- Редактор step-card: `step_id`, `role`, `prompt/title`, `depends_on`.
- Удобный выбор зависимостей (multiselect/checkbox), без ручного JSON.
- Сохранить `Advanced JSON` режим для power users.

## Acceptance criteria

- [ ] Оператор может создать workflow без редактирования JSON.
- [ ] Оператор может переключаться между Quick и Advanced без потери данных.
- [ ] Совместимость с текущим API payload сохранена.

## Implementation notes

Mapping поля `prompt` UI -> `title` API для обратной совместимости.

## Test plan

- [ ] Проверка валидации формы шагов и зависимостей.
- [ ] Проверка создания/обновления workflow через UI в обоих режимах.

## Risks and mitigations

- Risk: Дрейф состояния между Quick/Advanced режимами.
- Mitigation: Единый внутренний state + двусторонняя сериализация.

## Result

В работе.
- Commits: `<sha1>`
