# Task 050: Assistant-Facing Orchestration API (Chat-Friendly)

## Metadata

- Status: `in_progress`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить удобный API слой для работы ассистента: создать план -> запустить N агентов -> получить агрегированный статус/результат.

## Scope

- Endpoint/contract для orchestration intents (plan/start/status/merge-report).
- Machine-readable summary для чата.
- Ограничения безопасности и approval hooks.

## Acceptance criteria

- [ ] Ассистент может запускать мультиагентный pipeline одной командой.
- [ ] Ассистент получает структурированный итог без ручного парсинга логов.
- [ ] Сохранён контроль через approval policy.

## Test plan

- [ ] API contract tests.
- [ ] End-to-end chat-driven scenario.

## Result

- Commits: `<sha1>`
