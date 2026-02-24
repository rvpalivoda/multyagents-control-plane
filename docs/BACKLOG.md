# Backlog

## Priority legend

- `P0` critical
- `P1` high
- `P2` medium
- `P3` low

## Epics

### EPIC-0 Governance
- `TASK-001` (`P0`, `done`): Establish project control process and task governance

### EPIC-1 Platform foundation
- `TASK-016` (`P0`, `done`): Bootstrap monorepo structure (`apps/ui`, `apps/api`, `apps/telegram-bot`, `apps/host-runner`, `infra/compose`)
- `TASK-002` (`P0`, `done`): Add base docker-compose for core services
- `TASK-003` (`P1`, `done`): Add shared API contracts and schema versioning
- `TASK-030` (`P0`, `done`): Add one-command local launcher for full stack lifecycle
- `TASK-031` (`P1`, `done`): Add Electron desktop wrapper for launcher commands

### EPIC-2 Core orchestration
- `TASK-004` (`P0`, `done`): Implement project CRUD and local path policy
- `TASK-005` (`P0`, `done`): Implement role CRUD from UI
- `TASK-006` (`P0`, `done`): Implement workflow DAG CRUD from UI
- `TASK-017` (`P1`, `done`): Extend role model with prompts/tools/skill packs/constraints
- `TASK-020` (`P1`, `done`): Add project management UI with API update/delete support
- `TASK-028` (`P1`, `done`): Add task listing API and UI task explorer
- `TASK-034` (`P0`, `done`): Add event and artifact contract plus persistence APIs
- `TASK-035` (`P1`, `done`): Enable artifact-based handoff in workflow DAG
- `TASK-036` (`P1`, `done`): Implement skill-pack management in API and UI
- `TASK-037` (`P1`, `done`): Improve control-panel UX navigation and approvals workflow
- `TASK-038` (`P1`, `done`): Migrate UI to Tailwind and deliver full-width modern admin layout
- `TASK-039` (`P1`, `done`): Switch admin panel to light theme and polish readability
- `TASK-040` (`P0`, `done`): Redesign admin IA with operations dashboard and runs center split-view
- `TASK-041` (`P1`, `done`): Refactor admin UI into modular React components

### EPIC-3 Execution and runner
- `TASK-007` (`P0`, `done`): Implement host runner protocol (submit/cancel/status)
- `TASK-008` (`P0`, `done`): Implement `no-workspace` execution mode
- `TASK-009` (`P1`, `done`): Implement `shared-workspace` execution mode with path locks
- `TASK-018` (`P1`, `done`): Implement host-runner background execution lifecycle (mock + shell modes)
- `TASK-021` (`P0`, `done`): Add runner status callback sync and automatic lock release
- `TASK-022` (`P0`, `done`): Add native codex executor mode in host-runner
- `TASK-023` (`P0`, `done`): Propagate task/run cancel actions to host-runner
- `TASK-024` (`P0`, `done`): Add workflow DAG run expansion and dispatch-ready endpoint
- `TASK-026` (`P0`, `done`): Implement isolated-worktree mode with git worktree lifecycle
- `TASK-032` (`P0`, `done`): Implement docker-sandbox execution mode
- `TASK-033` (`P1`, `done`): Harden docker-sandbox isolation and path policy

### EPIC-4 Human-in-the-loop
- `TASK-010` (`P1`, `done`): Telegram bot command set (`run/status/approve/pause/resume/abort`)
- `TASK-011` (`P1`, `done`): Approval gating in orchestration lifecycle
- `TASK-025` (`P1`, `done`): Extend Telegram commands with `next` and `cancel`

### EPIC-5 Reliability and visibility
- `TASK-012` (`P1`, `done`): Event timeline and run audit trail UI
- `TASK-013` (`P1`, `done`): Integration tests for one code workflow and one text workflow
- `TASK-014` (`P1`, `done`): Create project skill pack for autonomous multi-agent delivery
- `TASK-019` (`P1`, `done`): Add API state snapshot persistence for restart resilience
- `TASK-027` (`P1`, `done`): Auto-update workflow run status from task lifecycle outcomes
- `TASK-029` (`P0`, `done`): Add end-to-end smoke test runner for docker stack + host runner

### EPIC-6 Knowledge providers
- `TASK-015` (`P1`, `done`): Integrate Context7 into role/task policy, runner payloads, and UI controls


### EPIC-7 Workflow authoring UX
- `TASK-042` (`P0`, `in_progress`): Workflow builder quick-create UX
- `TASK-043` (`P0`, `todo`): Inline validation and cycle prevention in workflow builder
- `TASK-044` (`P1`, `todo`): Add UI test harness and critical workflow builder tests
- `TASK-045` (`P1`, `todo`): Update operator docs for workflow creation

## Operating rule

Before starting implementation, create/update task file from template:
- `docs/tasks/TASK-<id>.md`
