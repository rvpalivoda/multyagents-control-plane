# Task 033: Harden docker-sandbox isolation and path policy

## Metadata

- Status: `in_progress`
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

- [ ] Sandbox tasks mount only allowed project paths.
- [ ] Task is rejected before execution when requested mount violates project policy.
- [ ] Security defaults are applied and logged for each sandbox run.
- [ ] Lifecycle events are visible in task/run event timeline.

## Implementation notes

Start with strict defaults and explicit allowlist exceptions. Keep policy evaluation in API and runtime enforcement in host-runner.

## Test plan

- [ ] Unit tests for path-policy validation.
- [ ] Runner tests for mount rendering and policy rejection paths.
- [ ] Integration test proving forbidden path is blocked.

## Risks and mitigations

- Risk: Overly strict defaults break legitimate toolchains.
- Mitigation: Add explicit per-role/per-task overrides with audit.

## Result

Planned.
