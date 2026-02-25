# Task 054: Assistant Control Loop (Plan->Spawn->Aggregate)

## Metadata

- Status: `in_progress`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Сделать контур, где ассистент одной командой запускает комплексную работу: декомпозиция -> параллельные агенты -> агрегация результата -> отчёт.

## Scope

- API contract для orchestration intent.
- Структурированный execution summary для чата.
- Safety hooks (approval-required stages).

## Acceptance criteria

- [ ] Один запрос ассистента запускает мультишаговый план.
- [ ] Есть machine-readable итог с результатами всех веток.
- [ ] Поддержаны ошибки/partial completion.

## Test plan

- [ ] API tests + one end-to-end orchestrated scenario.

## Result

- Commits: `<sha1>`
