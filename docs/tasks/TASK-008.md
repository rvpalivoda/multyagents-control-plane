# Task 008: Implement no-workspace execution mode

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Add explicit execution mode handling with default `no-workspace` and propagate it through API/UI/runner payload.

## Non-goals

- Implement shared lock manager or isolated worktree mechanics.
- Docker sandbox runtime execution.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#5-execution-modes`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Add `execution_mode` to task models.
- Default to `no-workspace`.
- Include resolved execution mode in runner payload.
- Add UI control for execution mode on task form.

## Acceptance criteria

- [x] Task create/read models include `execution_mode`.
- [x] Dispatch payload includes `execution_mode`.
- [x] UI can set `execution_mode` when creating task.
- [x] API tests and UI build pass.

## Implementation notes

Introduce full enum now (`no-workspace`, `shared-workspace`, `isolated-worktree`, `docker-sandbox`) while implementing behavior only for `no-workspace` path.

## Test plan

- [x] API tests verify default and explicit execution mode behavior.
- [x] UI build check after task form updates.

## Risks and mitigations

- Risk: future mode behaviors diverge from current payload contract.
- Mitigation: keep mode enum explicit and centralized in schema/contracts.

## Result

Implemented:
- Added `execution_mode` enum and task field in API schemas.
- Set default mode to `no-workspace`.
- Added `execution_mode` to runner payload and runner submit request.
- Updated host-runner submit model to accept execution mode.
- Updated shared contracts (`packages/contracts`) with execution mode.
- Added UI control for task execution mode.

Verification:
- `apps/api`: `pytest` -> `19 passed`
- `apps/host-runner`: `pytest` -> `2 passed`
- `apps/telegram-bot`: `pytest` -> `2 passed`
- `apps/ui`: `npm run build` succeeded

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
