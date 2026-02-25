# Task 059: Developer Workflow Pack (Feature/Bugfix/Release/Incident)

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить пресеты workflow для разработки ПО, чтобы ассистент мог запускать типовые процессы в 1-2 шага.

## Scope

- Feature delivery preset.
- Bugfix fast lane preset.
- Release prep and incident hotfix presets.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Workflow UX guide: `docs/WORKFLOW_CREATION_GUIDE.md`

## Acceptance criteria

- [x] Реализовано минимально полезно для ежедневной работы.
- [x] Видно прогресс/результаты в UI и API.
- [x] Покрыто targeted tests.

## Implementation notes

- В `apps/ui/src/App.tsx` расширен встроенный quick-create preset catalog для developer workflows:
  - `feature-delivery`
  - `bugfix-fast-lane`
  - `release-prep-lane`
  - `incident-hotfix-lane`
- Новые developer presets интегрированы в существующий preset selector и `Apply preset` flow без изменения API контракта.
- В `docs/WORKFLOW_CREATION_GUIDE.md` добавлены concise when-to-use рекомендации для developer workflow pack.
- В `apps/ui/src/App.workflowBuilder.test.tsx` добавлены/обновлены targeted tests:
  - проверка применения всех developer presets (scenario + default workflow name + step chain);
  - проверка launch validation при невалидном `Template ID`;
  - проверка quick launch с ручным валидным `Template ID`.

## Test plan

- [x] Targeted UI tests + UI build smoke.

## Result

- Verification:
  - `cd apps/ui && npm ci --ignore-scripts` -> passed (dependency install for sandbox).
  - `cd apps/ui && npm test -- App.workflowBuilder.test.tsx` -> passed (`1 file`, `10 tests`).
  - `cd apps/ui && npm run build` -> passed (production bundle in `apps/ui/dist`).
  - Note: test run prints `WebSocket server error: listen EPERM ... 24678` in this sandbox, but exits with code `0`.
- Commits:
  - Not recorded in this sandbox: `git commit` failed with `Permission denied` on `.git/worktrees/.../index.lock`.
