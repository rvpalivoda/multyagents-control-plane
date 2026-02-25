# Task 049: Recovery Playbooks and Auto-Retry Strategy

## Metadata

- Status: `todo`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Снизить ручную операционную нагрузку: авто-ретраи на типовые сбои и встроенные runbooks для быстрого восстановления.

## Scope

- Retry policy per step type (network, flaky tests, transient runner errors).
- UI/Telegram подсказки "что делать дальше" при fail/block.
- Runbook docs для топ-5 частых сбоев.

## Acceptance criteria

- [ ] Типовые transient ошибки восстанавливаются автоматом по policy.
- [ ] Для невосстановленных ошибок есть понятный recovery path.
- [ ] Снижен % ручных перезапусков.

## Test plan

- [ ] Fault-injection tests + retry assertions.

## Result

- Commits: `<sha1>`
