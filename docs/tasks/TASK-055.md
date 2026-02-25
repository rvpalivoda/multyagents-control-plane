# Task 055: Content Workflow Pack (Article/Social/Localization)

## Metadata

- Status: `in_progress`
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

## Acceptance criteria

- [ ] Доступны минимум 3 пресета контент-пайплайнов.
- [ ] Пресеты запускаются без ручного JSON редактирования.
- [ ] Есть краткая операторская документация по использованию.

## Test plan

- [ ] API/UI tests на создание и запуск шаблонов.
- [ ] Smoke на запуск каждого пресета.

## Result

- Commits: `<sha1>`
