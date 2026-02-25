# Task 042: Workflow Builder Quick Create UX

## Metadata

- Status: `done`
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

- [x] Оператор может создать workflow без редактирования JSON.
- [x] Оператор может переключаться между Quick и Advanced без потери данных.
- [x] Совместимость с текущим API payload сохранена.

## Implementation notes

Mapping поля `prompt` UI -> `title` API для обратной совместимости.

## Test plan

- [x] Проверка валидации формы шагов и зависимостей.
- [x] Проверка создания/обновления workflow через UI в обоих режимах.

## Risks and mitigations

- Risk: Дрейф состояния между Quick/Advanced режимами.
- Mitigation: Единый внутренний state + двусторонняя сериализация.

## Result

Реализован удобный quick-create редактор шагов workflow c синхронизацией в raw JSON режим.

Commits:
- `84fab1f` — quick-create editor и базовая inline-валидация.
- `88033d6` — интеграция с test harness и стабилизация тестов.
