# Task 044: UI Test Harness for Workflow Builder

## Metadata

- Status: `todo`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить тестовый контур UI (vitest + testing-library) для критичных сценариев workflow builder.

## Non-goals

- Полное покрытие всего UI.

## References

- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Базовая конфигурация vitest.
- Тесты сценариев Quick create + валидация.
- Тест синхронизации Quick/Advanced режимов.

## Acceptance criteria

- [ ] `npm test`/`vitest` запускается в `apps/ui`.
- [ ] Критичные тесты workflow builder проходят.

## Implementation notes

Приоритет на проверку business-логики, а не визуальных деталей.

## Test plan

- [ ] CI-совместимый запуск тестов.
- [ ] Локальный прогон на чистой установке.

## Risks and mitigations

- Risk: Флаки из-за async рендера.
- Mitigation: deterministic fixtures + await patterns.

## Result

- Commits: `<sha1>`
