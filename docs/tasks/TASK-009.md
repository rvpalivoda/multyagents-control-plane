# Task 009: Implement shared-workspace execution mode with path locks

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Implement `shared-workspace` execution mode so tasks can safely work in one project tree using soft path locks.

## Non-goals

- Full git worktree isolation (`isolated-worktree`).
- Per-task docker runtime (`docker-sandbox`).
- Distributed lock manager (single API process only for MVP).

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#5-execution-modes`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Extend task schema with shared mode workspace targeting (`project_id`, `lock_paths`).
- Validate lock paths against project root/allowlist.
- Acquire shared-workspace locks on dispatch and return conflict on overlap.
- Add explicit lock release API endpoint for operator/manual lifecycle control.
- Include workspace lock context in runner payload and task audit.

## Acceptance criteria

- [x] `shared-workspace` tasks require valid `project_id` and non-empty `lock_paths`.
- [x] Dispatch in shared mode acquires locks and exposes lock info in payload/audit.
- [x] Overlapping lock requests from another task return conflict (`409`).
- [x] Lock release endpoint frees paths and allows later dispatch.
- [x] API + host-runner tests pass; UI build passes.

## Implementation notes

Use in-memory soft locks keyed by normalized absolute paths.
Overlap rule is hierarchical: conflict when one lock path is equal to, parent of, or child of another lock path owned by a different task.

## Test plan

- [x] API tests for schema validation, conflict behavior, and release flow.
- [x] Host-runner tests for shared workspace submit payload compatibility.
- [x] UI build validation after task form changes.

## Risks and mitigations

- Risk: lock leaks if completion callback is missing.
- Mitigation: add explicit release endpoint and keep lock state observable in dispatch/audit.

## Result

Implemented:
- Extended task schema with `project_id` and `lock_paths`, including shared-workspace validation.
- Added shared workspace context in runner payload and task audit (`execution_mode`, `project_id`, `lock_paths`).
- Implemented in-memory soft path locks with overlap detection (`parent/child/equal`) and conflict handling.
- Added release endpoint: `POST /tasks/{task_id}/locks/release`.
- Updated runner client/host-runner submit contract to pass/validate shared workspace payload.
- Updated UI task form to configure `project_id` and `lock_paths` and to display known project IDs.
- Updated shared contract files in `packages/contracts`.

Verification:
- `apps/api`: `./.venv/bin/pytest -q` -> `23 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `4 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `2 passed`
- `apps/ui`: `npm run build` succeeded
