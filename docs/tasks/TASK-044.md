# Task 044: UI Test Harness for Workflow Builder

## Metadata

- Status: `done`
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

- [x] `npm test`/`vitest` запускается в `apps/ui`.
- [x] Критичные тесты workflow builder проходят.

## Implementation notes

Добавлен jsdom runtime, setup файл для cleanup и `@testing-library/jest-dom`.

## Test plan

- [x] CI-совместимый запуск тестов.
- [x] Локальный прогон на чистой установке.

## Risks and mitigations

- Risk: Флаки из-за async рендера.
- Mitigation: deterministic fixtures + await/waitFor patterns.

## Result

- Добавлен `vitest run` как основной тестовый скрипт UI.
- Добавлены unit тесты `workflowEditorUtils.test.ts`.
- Добавлены интеграционные UI тесты `App.workflowBuilder.test.tsx`.

Execution evidence:
- `cd apps/ui && npm test` -> passed (8 tests)

Commits:
- `<final-sha>`
