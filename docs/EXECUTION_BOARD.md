# Execution Board (MVP Closure)

## Purpose

Coordinate parallel delivery to move remaining work from `in_progress`/`review`/`todo` to `done` with commit and test evidence.

## Current baseline (2026-02-24)

- Total tasks: `36`
- `done`: `4`
- `in_progress`: `1`
- `review`: `29`
- `todo`: `2`

## Parallel lanes

### Lane A: Sandbox hardening

- Scope: `TASK-033`
- Skills: `host-runner-codex-cli`, `architecture-guard`, `testing-observability`
- Deliverables:
  - enforce runtime hardening defaults for docker sandbox
  - keep path policy validation strict and auditable
  - ensure lifecycle events are emitted and visible in timeline/audit

### Lane B: Artifact handoff in DAG

- Scope: `TASK-035`
- Skills: `workflow-dag-engine`, `events-artifacts-contract`, `api-orchestrator-fastapi`
- Deliverables:
  - artifact requirements in workflow step schema
  - dispatch-ready gating by dependency + artifact constraints
  - handoff references persisted in task/run records

### Lane C: Skill-pack management

- Scope: `TASK-036`
- Skills: `api-orchestrator-fastapi`, `react-control-panel`
- Deliverables:
  - skill-pack CRUD API and validation against catalog
  - role assignment to one or more skill-packs
  - UI for create/edit/delete plus usage visibility

### Lane D: Review-to-done burn-down

- Scope: all tasks in `review`
- Skills: `task-governance`, `testing-observability`
- Deliverables:
  - verify acceptance criteria
  - execute and record tests/evidence
  - record commit SHA in task `Result`
  - transition `review -> done`

## Quality gate

A task can move to `done` only when all conditions are met:
- acceptance criteria checked
- tests executed and recorded
- docs updated where behavior changed
- commit SHA listed in task `Result`

## MVP release gate

Release candidate starts when:
- `TASK-033`, `TASK-035`, `TASK-036` are `done`
- all `review` tasks are moved to `done` or explicitly returned to `in_progress` with blockers
- MVP exit criteria from `docs/IMPLEMENTATION_PLAN.md` are verified end-to-end
