# Architecture Blueprint (v0.1)

## 1. High-level design

Control Plane runs in Docker. Agent execution uses local host Codex CLI.

Components:
- `ui` (React): roles, workflows, runs, logs, approvals.
- `api` (FastAPI, Python): orchestration, policy checks, run lifecycle.
- `postgres`: metadata and state.
- `redis`: queue/event stream.
- `telegram-bot` (Python): operator interaction channel.
- `host-runner` (Python host process): invokes local `codex` CLI and reports status.

## 2. Why host-runner exists

Requirement: `codex` must be local host CLI.
Therefore API sends execution requests to host-runner through local secure channel.

Suggested transport:
- local HTTP on loopback with token auth, or
- unix domain socket for stricter local-only exposure.

## 3. Main data model

- `projects`
- `agent_roles`
- `skill_packs`
- `workflow_templates`
- `workflow_steps`
- `workflow_runs`
- `task_runs`
- `artifacts`
- `events`
- `approvals`

## 4. Execution lifecycle

1. Operator triggers workflow run.
2. API validates project/policies and expands DAG.
3. Ready step is queued.
4. Runner picks task, launches codex session, streams logs/events.
5. Task emits artifact(s), status changes to success/failure.
6. Dependent tasks are unlocked only when required artifact handoff conditions are satisfied.
7. Approval gates block until operator decision.
8. Quality gates are evaluated per task and aggregated per run (`blocker`/`warn` checks).
9. Failed task/run states are auto-triaged into failure categories with suggested operator next actions.
10. Operator may trigger partial re-run for selected failed `task_ids`/`step_ids`; only selected failed branches are reset and re-dispatched.
11. Run completes with final summary.

## 5. Execution modes

- `no-workspace`: no file access required.
- `shared-workspace`: shared project path with soft path locks.
- `isolated-worktree`: temporary git worktree + branch per task.
- `docker-sandbox`: dedicated container for task runtime needs.

## 6. Inter-agent contract

Event schema (minimum):
- `event_type`
- `run_id`
- `task_id`
- `producer_role`
- `payload`
- `created_at`

Artifact schema (minimum):
- `artifact_type` (`text`, `file`, `diff`, `commit`, `report`)
- `location`
- `summary`
- `producer_task_id`

Task completion handoff schema (minimum):
- `summary`
- `next_actions[]`
- `open_questions[]`
- `artifacts[]` with `artifact_id` and `is_required`

## 7. Security model

- Project-level allowed root path.
- Optional allowlist for write paths.
- Role policy for tools/skills.
- Approval policy for risky operations (merge, destructive commands, external calls).

## 8. Context provider policy (Context7)

- Role default: `context7_enabled` (boolean).
- Task override: `context7_mode` (`inherit`, `force_on`, `force_off`).
- Resolution order:
  - `force_on` => enabled
  - `force_off` => disabled
  - `inherit` => role default
- Effective value must be persisted in task audit and forwarded to runner payload.

## 9. Deployment topology

- `docker-compose` for core services.
- host-runner started as local service (systemd or process manager).
- API knows runner endpoint via env config.

## 10. Testing strategy

- Unit tests: policy engine, DAG scheduling, schema validation.
- Integration tests: end-to-end run with mocked runner.
- Smoke test: real local runner invocation in dev environment.
- Test framework baseline: `pytest`.
