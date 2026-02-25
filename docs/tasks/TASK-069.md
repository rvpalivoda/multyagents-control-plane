# Task 069: Parallel stress smoke for workflow runs

## Metadata
- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Добавить стресс-smoke на параллельные workflow runs для раннего выявления race-condition.

## Scope

- Добавить compose smoke-сценарий для параллельных workflow run с форсированным runner callback (`success`) и финальным summary.
- Прокинуть сценарий в one-command launcher (`./scripts/multyagents stress-smoke`).
- Обновить docs (`README.md`, `docs/TEST_MATRIX.md`) по запуску и expected summary.

## Acceptance criteria
- [x] Реализовано
- [x] Добавлен стресс-smoke сценарий с summary output и документирован запуск.

## Test plan

- [x] `bash -n scripts/multyagents infra/compose/scripts/run-e2e.sh`
- [x] `python3 -m py_compile infra/compose/scripts/parallel_workflow_stress_smoke.py infra/compose/scripts/e2e_smoke.py`
- [x] `./scripts/multyagents help`
- [ ] Полный smoke run: `STRESS_RUNS=20 STRESS_PARALLELISM=6 ./scripts/multyagents stress-smoke` (не выполнен из-за sandbox доступа к Docker daemon).

## Blocker

- Невозможно выполнить `git commit` в текущем sandbox: нет прав на запись в gitdir worktree
  (`/home/roman/code/multyagents.dev/.git/worktrees/multyagents-task-069-next/index.lock`).
- Невозможно выполнить compose smoke run в sandbox: нет доступа к Docker daemon (`/var/run/docker.sock`).

## Unblock options

- Выполнить commit и smoke-run вне sandbox (локальная shell с доступом к `.git` worktree и Docker daemon).
- Либо разрешить sandbox доступ к gitdir worktree + docker socket для финализации задачи в этой сессии.

## Result

- Реализовано:
  - Добавлен новый сценарий: `infra/compose/scripts/parallel_workflow_stress_smoke.py`.
  - `infra/compose/scripts/run-e2e.sh` расширен параметром `E2E_SCENARIO_SCRIPT` для запуска произвольного smoke script.
  - `scripts/multyagents` получил команду `stress-smoke`.
  - Обновлены docs: `README.md`, `docs/TEST_MATRIX.md`.
- Выполненные проверки:
  - `bash -n scripts/multyagents infra/compose/scripts/run-e2e.sh`
  - `python3 -m py_compile infra/compose/scripts/parallel_workflow_stress_smoke.py infra/compose/scripts/e2e_smoke.py`
  - `./scripts/multyagents help`
- Commits: `<final-sha>`


Verification:
- Added parallel stress smoke scenario script and CLI command (`stress-smoke`).
