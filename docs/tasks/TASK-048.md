# Task 048: Shared Handoff Board for Agent-to-Agent Context

## Metadata

- Status: `todo`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать явный handoff-board между агентами: что сделано, что передать дальше, какие артефакты обязательны для следующего шага.

## Scope

- Структурированный handoff payload в task completion.
- UI панель handoff в run details.
- Валидация обязательных артефактов перед dispatch следующего шага.

## Acceptance criteria

- [ ] Следующий шаг получает структурированный handoff без ручного копипаста.
- [ ] Отсутствие обязательного handoff блокирует dispatch с понятной ошибкой.
- [ ] Handoff отражается в event timeline.

## Test plan

- [ ] Unit/integration tests handoff schema + blocking behavior.

## Result

- Commits: `<sha1>`
