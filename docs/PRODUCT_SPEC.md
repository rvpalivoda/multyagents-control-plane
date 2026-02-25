# Product Specification (v0.1)

## 1. Product intent

Build a universal multi-agent orchestration platform with a web control panel.
The platform coordinates many autonomous agents for coding and non-coding tasks.

## 2. Primary users

- Operator: configures projects, roles, workflows, policies, and runs.
- Reviewer: approves risky actions and merges.
- Observer: monitors progress and artifacts.

## 3. Core capabilities

1. Multi-project management
- Register project with local file path and optional git metadata.
- Restrict allowed paths per project.

2. Role management from UI
- Create role with:
  - name
  - goal/system prompt
  - allowed tools
  - skill packs
  - execution constraints

3. Workflow builder from UI
- DAG-based steps with dependencies.
- Workflow step authoring modes:
  - guided quick-create cards (`id`, `role`, `prompt`, `depends_on` picker with inline validation)
  - advanced raw JSON editor for power users
- Step config:
  - role
  - task type (`code`, `text`, `research`, `ops`, `custom`)
  - execution mode
  - retry/timeout policy
  - approval gates

4. Agent execution modes
- `no-workspace`
- `shared-workspace`
- `isolated-worktree`
- `docker-sandbox`

5. Inter-agent collaboration
- Event bus for machine-readable events.
- Artifact exchange (text, files, commits, reports).
- Structured task-completion handoff payload (`summary`, `next_actions`, `required artifacts`) for downstream steps.
- Optional direct handoff by dependency links in DAG.

6. Git integration
- Branch/worktree lifecycle for isolated mode.
- Soft path locks in shared mode.
- Reviewer gate before merge to protected branches.

7. Telegram integration
- Commands: status, run, pause, resume, approve, abort.
- Notifications for blockers, failures, and approval requests.
- Failed runs/tasks expose auto-triage category, operator hints, and suggested next actions in control interfaces.

8. Knowledge provider configuration
- Role-level default for Context7 usage.
- Task-level override (`inherit`, `force_on`, `force_off`).
- Resolved provider state visible in run/task audit.

## 4. Non-functional requirements

- Reliability: resumable runs after service restart.
- Auditability: full trace of role/task/policy/artifacts.
- Security: path restrictions and per-role tool policies.
- Observability: status transitions, structured logs, event history.
- Extensibility: new task types and tools without schema breakage.

## 5. Out of scope for v0.1

- Distributed multi-host scheduling.
- Advanced long-term memory across organizations.
- Marketplace of community workflows.

## 6. Acceptance criteria (MVP)

- Create/edit role entirely from UI.
- Create/edit workflow entirely from UI.
- Run workflow in at least 2 modes (`no-workspace`, `shared-workspace`).
- Execute local host `codex` via runner controlled by Dockerized API.
- Receive Telegram approval request and apply decision to run.
