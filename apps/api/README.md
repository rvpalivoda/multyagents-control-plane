# multyagents api

Minimal FastAPI service for orchestration and Context7 policy resolution.

Project management endpoints:
- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PUT /projects/{project_id}`
- `DELETE /projects/{project_id}`

Includes shared-workspace soft lock support:
- task fields: `project_id`, `lock_paths`
- dispatch lock acquisition for `execution_mode=shared-workspace`
- manual lock release endpoint: `POST /tasks/{task_id}/locks/release`
- auto lock release on runner terminal callback status

Includes isolated-worktree support:
- `execution_mode=isolated-worktree` requires `project_id`
- dispatch payload includes workspace metadata:
  - `worktree_path`
  - `git_branch`
- worktree sessions are run-aware and tracked in task audit:
  - `workflow_run_id`
  - `task_run_id`
  - `worktree_path`
  - `git_branch`
  - `worktree_cleanup_*` fields from runner callbacks

Includes docker-sandbox support:
- `execution_mode=docker-sandbox` requires:
  - `project_id`
  - `sandbox` config (`image`, `command`, optional `workdir`, `env`, `mounts`)
- when `sandbox.mounts` is empty, dispatch auto-mounts first allowed project path (or project root) to `sandbox.workdir`
- task audit stores sandbox metadata:
  - `sandbox_image`
  - `sandbox_workdir`
  - `sandbox_container_id`
  - `sandbox_exit_code`
  - `sandbox_error`

Includes approval gating support:
- task field: `requires_approval`
- approval endpoints:
  - `GET /tasks/{task_id}/approval`
  - `GET /approvals/{approval_id}`
  - `POST /approvals/{approval_id}/approve`
  - `POST /approvals/{approval_id}/reject`

Includes run timeline support:
- workflow run endpoints:
  - `POST /workflow-runs`
    - when created from `workflow_template_id` without explicit `task_ids`, run tasks are auto-created from template steps
    - optional `step_task_overrides` map supports per-step task settings (`context7_mode`, `execution_mode`, `requires_approval`, workspace/sandbox fields)
  - `GET /workflow-runs`
  - `GET /workflow-runs/{run_id}`
  - `POST /workflow-runs/{run_id}/pause`
  - `POST /workflow-runs/{run_id}/resume`
  - `POST /workflow-runs/{run_id}/abort`
    - abort also sends task cancel requests to host-runner for linked tasks
  - `POST /workflow-runs/{run_id}/dispatch-ready`
    - dispatches next DAG-ready task for the run
  - `POST /workflow-runs/{run_id}/control-loop`
    - executes one assistant control-loop tick over existing primitives:
      - `plan` dispatch candidates (dependencies + handoff + approval checks)
      - `spawn` ready tasks via runner submission
      - `aggregate` run/task summary in one response
  - `GET /workflow-runs/{run_id}/execution-summary`
    - machine-readable run summary for chat/assistant consumers
    - includes per-task statuses, dispatch plan state, and artifact/handoff rollups
- event timeline endpoint:
  - `GET /events` with optional `run_id`, `task_id`, `event_type`, `limit`
  - `POST /events` for external structured event ingestion
- artifact endpoints:
  - `GET /artifacts` with optional `run_id`, `task_id`, `artifact_type`, `limit`
  - `POST /artifacts` for structured artifact ingestion
  - event/artifact write contracts include `contract_version` (current `v1`)
- run status rollup:
  - auto `running/success/failed` based on task lifecycle outcomes
  - manual `aborted` remains authoritative
- auto-retry + recovery hints:
  - retry policy sources:
    - role-level: `execution_constraints.retry_policy`
  - retry policy shape:
    - `max_retries` (0..10)
    - `retry_on` (`network`, `flaky-test`, `runner-transient`)
  - transient failures (`submit-failed` or runner `failed`) can auto-schedule retry
  - workflow run payload includes:
    - `retry_summary`
    - `failure_categories`
    - `failure_triage_hints`
    - `suggested_next_actions`
  - task payload includes:
    - `failure_category`
    - `failure_triage_hints`
    - `suggested_next_actions`

Assistant-facing orchestration intents (chat-friendly):
- `POST /assistant/intents/plan`
  - returns resolved step plan (dependencies + per-step task config) and machine-readable summary
- `POST /assistant/intents/start`
  - creates workflow run from template, optionally dispatches all currently-ready tasks, reports approval-blocked tasks
- `POST /assistant/intents/status`
  - returns run/tasks snapshot with machine-readable rollup (`task_status_counts`, `ready_task_ids`, `blocked_by_approval_task_ids`, artifacts/handoffs coverage)
- `POST /assistant/intents/report`
  - returns aggregated run report (`events`, `artifacts`, `handoffs`) plus machine-readable summary for chat automation

Task runtime control:
- `GET /tasks` with optional `run_id` filter
- `POST /tasks/{task_id}/cancel` sends cancel request to host-runner and updates task state.

Role model supports policy configuration fields:
- `system_prompt`
- `allowed_tools`
- `skill_packs`
- `execution_constraints`

Optional snapshot persistence:
- set `API_STATE_FILE` to persist/restore API state across restarts.

Runner status synchronization:
- callback endpoint: `POST /runner/tasks/{task_id}/status`
- optional callback auth token: `API_RUNNER_CALLBACK_TOKEN` (expects `X-Runner-Token`)
- callback URL passed to host-runner via dispatch submit payload from:
  - `API_RUNNER_CALLBACK_BASE_URL` (preferred)
  - fallback `API_PUBLIC_BASE_URL`

CORS:
- `API_CORS_ALLOW_ORIGIN_REGEX` default: `^https?://(localhost|127\.0\.0\.1)(:\d+)?$`
- `API_CORS_ALLOW_ORIGINS` default: `null` (comma-separated fixed origins)
