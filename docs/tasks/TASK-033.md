# Task 033: Harden docker-sandbox isolation and path policy

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-24`

## Objective

Enforce project path restrictions and safe container runtime defaults for `docker-sandbox` mode.

## Non-goals

- Full container security benchmark compliance.
- Kubernetes policy engine integration.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#7-security-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Map project `root_path`/`allowed_paths` into controlled mounts for sandbox tasks.
- Add deny/allow checks before runner starts container.
- Add runtime policy defaults (read-only rootfs where possible, dropped caps, no privileged mode).
- Emit structured sandbox lifecycle events (`sandbox_started`, `sandbox_failed`, `sandbox_stopped`).

## Acceptance criteria

- [x] Sandbox tasks mount only allowed project paths.
- [x] Task is rejected before execution when requested mount violates project policy.
- [x] Security defaults are applied and logged for each sandbox run.
- [x] Lifecycle events are visible in task/run event timeline.

## Implementation notes

Start with strict defaults and explicit allowlist exceptions. Keep policy evaluation in API and runtime enforcement in host-runner.

## Test plan

- [x] Unit tests for path-policy validation.
- [x] Runner tests for mount rendering and policy rejection paths.
- [x] Integration test proving forbidden path is blocked.

## Risks and mitigations

- Risk: Overly strict defaults break legitimate toolchains.
- Mitigation: Add explicit per-role/per-task overrides with audit.

## Result

- Progress update (2026-02-24):
  - Fixed docker sandbox cancellation cleanup in host-runner so `docker rm -f <container>` is called on cancel.
  - Commit: `9270ece` (`fix(task-033): stop docker container on cancel`)
  - Validation:
    - `apps/host-runner`: `pytest -q tests/test_runner_api.py::test_cancel_docker_sandbox_forces_container_stop` -> passed
    - `apps/host-runner`: `pytest -q` -> `12 passed`
- Hardening completion update (2026-02-24):
  - Verified strict mount policy enforcement in API dispatch path (forbidden mounts rejected).
  - Verified sandbox lifecycle timeline events (`sandbox.started`, `sandbox.stopped`).
  - Verified host-runner security defaults in docker command (`read-only`, caps drop, no-new-privileges, resource/network limits).
  - Validation:
    - `apps/api`: `pytest -q` -> `65 passed`
    - `apps/host-runner`: `pytest -q` -> `12 passed`
  - Commits:
    - `9270ece` (`fix(task-033): stop docker container on cancel`)
    - `<pending commit sha>`
