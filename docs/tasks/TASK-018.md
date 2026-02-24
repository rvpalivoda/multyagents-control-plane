# Task 018: Implement host-runner background execution lifecycle (mock + shell modes)

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Upgrade host-runner from static queue stub to background execution lifecycle with status transitions.

## Non-goals

- Production-grade process supervisor.
- Guaranteed force-kill semantics for all executors.
- Full codex CLI argument matrix.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Add background execution after submit.
- Add status transitions: `queued -> running -> success|failed|canceled`.
- Add default `mock` executor and optional `shell` executor mode via env.
- Extend runner task model with execution metadata (`stdout`, `stderr`, `exit_code`, timestamps).
- Extend tests for lifecycle behavior.

## Acceptance criteria

- [x] Submitted task eventually reaches terminal status in mock mode.
- [x] Cancel request can stop mock execution and set canceled status.
- [x] Runner task response includes execution metadata fields.
- [x] Host-runner tests cover new lifecycle behavior.

## Implementation notes

Default executor remains `mock` for stable local development and tests.
Shell mode is opt-in via `HOST_RUNNER_EXECUTOR=shell` and command template env var.

## Test plan

- [x] Host-runner unit/API tests for success and cancel lifecycle.
- [x] Full regression of api/ui tests.

## Risks and mitigations

- Risk: race conditions in background state updates.
- Mitigation: guard task map mutations with a lock.

## Result

Implemented:
- Added background execution lifecycle in host-runner:
  - `queued -> running -> success|failed|canceled`
- Added execution metadata fields to `RunnerTask`:
  - `executor`, timestamps, `exit_code`, `stdout`, `stderr`
- Added default `mock` executor with cancellable loop.
- Added optional `shell` executor with env-based command template:
  - `HOST_RUNNER_EXECUTOR=shell`
  - `HOST_RUNNER_CMD_TEMPLATE` with `{prompt}`, `{task_id}`, `{run_id}`
- Added lock-guarded task state mutation to reduce race conditions.
- Extended host-runner tests with terminal lifecycle and metadata assertions.

Verification:
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `5 passed`
- `apps/api`: `./.venv/bin/pytest -q` -> `31 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/ui`: `npm run build` succeeded

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
