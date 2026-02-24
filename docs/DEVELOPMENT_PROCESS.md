# Development Process (Spec-First, Task-Driven)

## 1. Purpose

Keep development predictable, auditable, and controllable for a local personal multi-agent project.

## 2. Mandatory artifacts

Every non-trivial change must map to:
- product requirement in `docs/PRODUCT_SPEC.md`
- technical design in `docs/ARCHITECTURE.md`
- execution step in `docs/IMPLEMENTATION_PLAN.md`
- a task document based on `docs/templates/TASK_TEMPLATE.md`

## 3. Task lifecycle

Use these statuses only:
1. `todo`
2. `in_progress`
3. `blocked`
4. `review`
5. `done`
6. `canceled`

State transitions:
- `todo` -> `in_progress`
- `in_progress` -> `blocked` or `review`
- `blocked` -> `in_progress` or `canceled`
- `review` -> `done` or `in_progress`

## 4. Task creation rules

Each task must include:
- objective and non-goals
- linked spec sections
- linked architecture sections
- explicit acceptance criteria
- test plan (how completion is verified)
- risk notes (if any)

No implementation starts before acceptance criteria are written.

## 5. Branch and commit rules

- Main branch is `master`.
- One task -> one branch (`task/<id>-<slug>`) unless task is tiny.
- At least one commit is mandatory for every task moved to `review` or `done`.
- Task status `done` requires commit evidence: at least one SHA must be listed in task `Result`.
- Commit message format:
  - `feat(task-<id>): ...`
  - `fix(task-<id>): ...`
  - `docs(task-<id>): ...`
  - `refactor(task-<id>): ...`

## 6. Definition of done per task

A task is `done` only if:
1. Acceptance criteria are met.
2. Tests/checks were executed (or explicitly documented why not).
3. Docs updated where behavior changed.
4. At least one commit exists for the task and commit SHA is recorded in task `Result`.
5. Task document updated with final result and evidence.

## 7. Blocker protocol

If blocked:
1. move task to `blocked`
2. write exact blocker description
3. propose at least one unblocking option
4. decide: continue, split, or cancel

## 8. Weekly control loop (personal mode)

At minimum once per week:
1. Review `docs/BACKLOG.md`
2. Re-prioritize tasks by impact/risk
3. Archive completed tasks
4. Create ADR entries for architecture decisions that changed
