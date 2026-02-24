---
name: task-governance
description: Manage development tasks with strict lifecycle, acceptance criteria, and completion evidence. Use when creating, splitting, reprioritizing, or closing tasks in this repository, or when converting free-form requests into actionable tracked work.
---

# Task Governance

## Overview

Drive every non-trivial change through a task file and explicit status transitions.
Keep scope, acceptance criteria, and verification evidence auditable.

## Workflow

1. Identify task intent.
2. Map the task to product and architecture sections.
3. Create or update `docs/tasks/TASK-<id>.md` from template.
4. Fill acceptance criteria before implementation.
5. Move status through allowed states only.
6. Record evidence in `Result` before setting `done`.

## Required checks

- Use only statuses: `todo`, `in_progress`, `blocked`, `review`, `done`, `canceled`.
- Keep one owner and one priority per task.
- If blocked, write blocker and at least one unblock option.
- If scope changed, update acceptance criteria before coding.

## Files to use

- `docs/DEVELOPMENT_PROCESS.md`
- `docs/BACKLOG.md`
- `docs/templates/TASK_TEMPLATE.md`
- `docs/tasks/`

For concise checklists, read `references/task-checklists.md`.
