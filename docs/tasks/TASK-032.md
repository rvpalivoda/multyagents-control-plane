# Task 032: Implement docker-sandbox execution mode

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-24`

## Objective

Add first-class `docker-sandbox` task execution mode through API orchestration and host-runner.

## Non-goals

- Multi-host scheduling or remote container clusters.
- Production-grade image signing policy.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#5-execution-modes`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-4-git-and-isolation-4-5-days`

## Scope

- Extend task/workflow validation to accept `execution_mode=docker-sandbox`.
- Extend runner payload with sandbox config (`image`, `workdir`, `command`, `env`, `mounts`).
- Implement host-runner path to create/run/stop container per task.
- Persist sandbox runtime metadata in task audit (`container_id`, `exit_code`, error reason).

## Acceptance criteria

- [x] Workflow/task creation accepts `docker-sandbox` mode and validates required fields.
- [x] Host-runner executes a task in Docker container and reports status/logs back to API.
- [x] Cancel action stops active sandbox container and task status is synchronized.
- [x] Integration test covers one successful `docker-sandbox` run end-to-end.

## Implementation notes

Keep API as scheduler/source of truth and keep container lifecycle in host-runner. Reuse existing runner callback contract to avoid protocol fork.

## Test plan

- [x] API unit tests for schema/validation and dispatch payload generation.
- [x] Host-runner tests for run/cancel lifecycle in docker mode.
- [x] Integration test for docker-sandbox run lifecycle.

## Risks and mitigations

- Risk: Host Docker daemon availability differs by environment.
- Mitigation: Fail fast with explicit diagnostics and fallback recommendation.

## Result

Implemented:

- API schema support for docker sandbox payloads:
  - task field `sandbox`
  - runner payload field `sandbox`
  - runner callback field `container_id`
- Store dispatch and policy handling:
  - docker workspace context resolution
  - sandbox mount validation against project root/allowed paths
  - default mount derivation when mounts are omitted
  - task audit metadata persistence for sandbox runtime (`container_id`, `exit_code`, error)
- Host-runner docker execution path:
  - `docker run --rm` execution with mounts/env/workdir/command
  - deterministic container naming
  - cancel path force-stop via `docker rm -f`
  - callback emission with `container_id`

Verification:

- `cd apps/api && .venv/bin/pytest -q` -> `53 passed`
- `cd apps/host-runner && .venv/bin/pytest -q` -> `12 passed`
