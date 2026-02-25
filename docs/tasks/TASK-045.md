# Task 045: Workflow Builder Operator Guide Update

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Обновить документацию по созданию workflow в UI (Quick create + Advanced).

## Non-goals

- Полный rewrite всей документации проекта.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Краткая инструкция в README и/или docs.
- Описание ограничений и best practices (идентификаторы шагов, зависимости).
- Мини pre-run checklist перед запуском workflow run.

## Acceptance criteria

- [x] Новый оператор может создать валидный workflow по инструкции.
- [x] Описан переход Quick <-> Advanced.

## Implementation notes

Добавлен отдельный операторский гайд, README обновлен ссылкой.

## Test plan

- [x] Ручная верификация документации по шагам (сверено с UI и текущими validation правилами).

## Risks and mitigations

- Risk: Документация отстанет от UI.
- Mitigation: Ссылки на task/commit evidence и регулярная сверка при UI-изменениях.

## Result

- Добавлен `docs/WORKFLOW_CREATION_GUIDE.md`.
- Обновлен `README.md` ссылкой на guide.
- Обновлен backlog/статусы задач EPIC-7.

Commits:
- `<final-sha>`
