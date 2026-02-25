# Task 046: Agent-Oriented Workflow Templates (Operator + Assistant)

## Metadata

- Status: `in_progress`
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

- [ ] Оператор запускает один из шаблонов без ручной сборки DAG.
- [ ] Шаблоны создают валидные workflow и успешно стартуют run.
- [ ] Есть короткое описание сценария для каждого шаблона.

## Test plan

- [ ] API/UI tests на создание и запуск шаблонов.
- [ ] E2E smoke по одному прогону на template.

## Result

- Commits: `<sha1>`
