# Task 060: Local Runtime Bootstrap & Healthpack

## Metadata

- Status: `in_progress`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать стабильный локальный запуск через compose + единый healthcheck/scaffold.

## Scope

- Стандартизировать docker compose локальный запуск (api/ui/runner/telegram-bot опционально).
- Добавить scripts/local-smoke.sh (health endpoints + test run).
- Добавить docs по required env и quickstart для локальной работы.

## Acceptance criteria

- [ ] Реализовано минимально полезно для ежедневной локальной работы.
- [ ] Виден прозрачный результат/процесс в UI/API/docs.
- [ ] Покрыто targeted tests и smoke.

## Test plan

- [ ] API/UI tests + локальный smoke-run.

## Result

- Commits: `<sha1>`
