# Task 011: Approval gating in orchestration lifecycle

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Add approval gate mechanics so selected tasks cannot be dispatched until explicitly approved.

## Non-goals

- Full workflow-run scheduler state machine.
- Multi-approver quorum logic.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-3-human-in-the-loop-2-3-days`

## Scope

- Extend task model with `requires_approval`.
- Create approval entities (`pending`, `approved`, `rejected`) linked to tasks.
- Block dispatch when approval is pending/rejected.
- Add API endpoints to read and decide approvals.
- Add tests for dispatch blocking and approval transitions.

## Acceptance criteria

- [x] Tasks can declare approval requirement at creation.
- [x] Dispatch is blocked until task approval is `approved`.
- [x] API provides read/approve/reject endpoints for approvals.
- [x] Tests cover pending/approved/rejected flows.

## Implementation notes

Use one approval record per task for MVP.
On task creation with `requires_approval=true`, create pending approval immediately.

## Test plan

- [x] API tests for approval lifecycle and dispatch gating.

## Risks and mitigations

- Risk: stale pending approvals can block task forever.
- Mitigation: explicit endpoints to query state and update decision.

## Result

Implemented:
- Added task field `requires_approval` with default `false`.
- Added approval entity model with statuses: `pending`, `approved`, `rejected`.
- Added per-task approval lifecycle in API store and dispatch gating before runner submit.
- Added approval endpoints:
  - `GET /tasks/{task_id}/approval`
  - `GET /approvals/{approval_id}`
  - `POST /approvals/{approval_id}/approve`
  - `POST /approvals/{approval_id}/reject`
- Extended task audit with approval metadata.
- Added UI task form checkbox for `requires_approval`.

Verification:
- `apps/api`: `./.venv/bin/pytest -q` -> `26 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `9 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `4 passed`
- `apps/ui`: `npm run build` succeeded
