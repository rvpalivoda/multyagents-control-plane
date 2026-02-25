# Task 047: Parallel Worktree Session Manager

## Metadata

- Status: `todo`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать безопасный и удобный менеджер параллельных worktree-сессий для нескольких агентов с автоматической очисткой и трассировкой.

## Scope

- Автосоздание worktree/branch на task-run.
- Явная связь `task_run -> worktree_path -> branch` в audit.
- Cleanup policy при success/failure/cancel.
- Защита от конфликтов путей.

## Acceptance criteria

- [ ] Для параллельных задач worktree изолированы и не конфликтуют.
- [ ] Cleanup выполняется автоматически и логируется.
- [ ] В UI видно где работал агент и какой branch создан.

## Test plan

- [ ] Integration tests для 2-3 параллельных задач.
- [ ] Негативный кейс: коллизия branch/worktree.

## Result

- Commits: `<sha1>`
