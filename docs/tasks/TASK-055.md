# Task 055: Content Workflow Pack (Article/Social/Localization)

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать набор готовых workflow-шаблонов для мультиагентного создания текстового контента, чтобы запускать производство контента в 1-2 шага.

## Scope

- Шаблоны:
  - Article pipeline: research -> outline -> draft -> edit -> fact-check -> final
  - Social pipeline: ideas -> hooks -> variants -> QA -> final
  - Localization pipeline: source -> adapt -> tone QA -> final
- Quick launch UX для этих шаблонов.
- Совместимость с текущим workflow contracts.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-3-human-in-the-loop-2-3-days`

## Acceptance criteria

- [x] Доступны минимум 3 пресета контент-пайплайнов.
- [x] Пресеты запускаются без ручного JSON редактирования.
- [x] Есть краткая операторская документация по использованию.

## Implementation notes

- В `apps/ui/src/App.tsx` расширен набор встроенных presets:
  - `article pipeline`
  - `social pipeline`
  - `localization pipeline`
- Для каждого preset добавлены:
  - сценарное описание;
  - дефолтное имя workflow;
  - DAG-цепочка шагов с зависимостями.
- Пресеты продолжают работать через существующий `Quick create` + `Quick launch` UX без ручного JSON.
- В `apps/ui/src/App.workflowBuilder.test.tsx` добавлены/расширены тесты:
  - применение всех трех content presets;
  - создание workflow из `article pipeline` и quick launch run без перехода в `Raw JSON`.
- Обновлена операторская документация `docs/WORKFLOW_CREATION_GUIDE.md` с concrete examples.

## Test plan

- [x] API/UI tests на создание и запуск шаблонов.
- [x] Smoke на запуск каждого пресета.

## Result

- Verification:
  - `cd apps/ui && npm test -- App.workflowBuilder.test.tsx` -> passed (`8 passed`).
  - `cd apps/ui && npm run build` -> passed (production build created under `apps/ui/dist`).
  - Note: test run prints `WebSocket server error: listen EPERM ... 24678` in this sandbox, but suite exits with code `0` and all tests pass.
- Commits:
  - Not recorded in this sandbox: `git commit` fails with `Permission denied` on `.git/worktrees/.../index.lock`.
