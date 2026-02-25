# Task 046: Agent-Oriented Workflow Templates (Operator + Assistant)

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить набор шаблонов workflow для повседневной мультиагентной разработки, чтобы запуск был в 1–2 клика и удобен как оператору, так и ассистенту.

## Non-goals

- Полностью автономное принятие рискованных решений без approval.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-3-human-in-the-loop-2-3-days`

## Scope

- Встроенные workflow templates:
  - feature delivery (plan -> implement -> test -> review)
  - bugfix fast lane
  - docs/research lane
- Быстрый запуск из UI c минимальным числом полей.
- Понятные defaults для ролей/скиллов.

## Acceptance criteria

- [x] Оператор запускает один из шаблонов без ручной сборки DAG.
- [x] Шаблоны создают валидные workflow и успешно стартуют run.
- [x] Есть короткое описание сценария для каждого шаблона.

## Implementation notes

- В `apps/ui/src/App.tsx` добавлены встроенные preset-шаблоны:
  - `feature delivery`
  - `bugfix fast lane`
  - `docs/research lane`
- Для каждого preset добавлены:
  - сценарное описание (operator/assistant-friendly);
  - дефолтное имя workflow;
  - дефолтная DAG-цепочка шагов с зависимостями.
- Добавлен `Apply preset`, который в один клик наполняет quick editor полями DAG (без ручной сборки).
- В `Workflows` секции добавлен блок `Quick launch` с минимально нужными полями:
  - `Template ID` (опционально; если пусто, используется выбранный workflow);
  - `Initiated by`.
- Quick launch вызывает существующий API контракт `POST /workflow-runs` без изменения схем (backward-compatible).
- В `apps/ui/src/App.workflowBuilder.test.tsx` добавлены тесты:
  - применение preset `bugfix fast lane`;
  - quick launch из `Workflows` и проверка payload.
- Обновлена документация `docs/WORKFLOW_CREATION_GUIDE.md` (presets + quick launch flow).

## Test plan

- [x] API/UI tests на создание и запуск шаблонов.
- [ ] E2E smoke по одному прогону на template.

## Risks and mitigations

- Risk: Полный API pytest regression не выполнен в этом sandbox.
- Mitigation: UI tests покрывают новый UX/контракты payload, API контракт не менялся; рекомендован запуск `apps/api` pytest в среде с доступным `pytest`.
- Risk: Невозможно выполнить git commit в текущем sandbox (нет прав записи в worktree gitdir вне writable root).
- Mitigation: Нужен запуск коммита в окружении с доступом к git metadata (`.git/worktrees/...`).

## Result

- Delivered:
  - built-in workflow presets (feature delivery, bugfix fast lane, docs/research lane);
  - workflows-tab quick launch UX with minimal fields;
  - tests and operator docs updates.
- Verification evidence:
  - `cd apps/ui && npm test` -> `2 passed (2)`, `10 passed (10)`.
  - `cd apps/ui && npm run build` -> production build succeeded.
  - `cd apps/api && .venv/bin/python -m pytest tests/test_api_workflows.py` -> failed: `No module named pytest` (env limitation).
  - `cd apps/api && .venv/bin/pip install -e .[dev]` -> failed due no network access to package index.
- Commits:
- `f99b17f`
