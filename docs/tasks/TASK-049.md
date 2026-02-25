# Task 049: Recovery Playbooks and Auto-Retry Strategy

## Metadata

- Status: `in_progress`
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

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`

## Acceptance criteria

- [ ] Типовые transient ошибки восстанавливаются автоматом по policy.
- [ ] Для невосстановленных ошибок есть понятный recovery path.
- [ ] Снижен % ручных перезапусков.

## Test plan

- [x] Fault-injection tests + retry assertions (added in `apps/api/tests/test_api_retry_strategy.py`).
- [ ] Execute API/Telegram/UI tests in this environment (blocked: missing runtime deps and sandbox limits).

## Current status

- Проведён исследовательский проход и подготовлены изменения/наброски в API/Telegram/docs.
- Полная интеграция retry policy временно отложена, чтобы не ломать handoff-поток из TASK-048.

## Next steps

1. Реализовать retry policy в отдельном слое dispatch/retry без регресса handoff контрактов.
2. Добавить recovery playbook и triage hints в API/Telegram payload.
3. Закрыть targeted tests по retry стратегии.

## Result

- Commits: `<pending>`
