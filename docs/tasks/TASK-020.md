# Task 020: Add project management UI with API update/delete support

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Provide full project management flow from control panel, including project edit/delete operations.

## Non-goals

- Full per-project authorization and tenancy.
- Filesystem existence checks for project roots.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#7-security-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add API endpoints:
  - `PUT /projects/{id}`
  - `DELETE /projects/{id}`
- Add store logic for project update/delete with conflict guard.
- Add UI section to create/list/select/update/delete projects.
- Extend tests for new API behavior.

## Acceptance criteria

- [x] Projects can be updated from API/UI.
- [x] Projects can be deleted when not linked; conflicts return `409`.
- [x] UI exposes create/list/update/delete for projects.
- [x] Tests cover update/delete/conflict behavior.

## Implementation notes

Project delete should be blocked if referenced by workflow templates or tasks.

## Test plan

- [x] Extend API project tests.
- [x] Run full API + UI + service regressions.

## Risks and mitigations

- Risk: deleting project while locks/tasks still reference paths.
- Mitigation: return `409` on linked project references.

## Result

Implemented project update/delete end-to-end:

- API: `PUT /projects/{project_id}` and `DELETE /projects/{project_id}`.
- Store: update/delete project operations with `409` conflict protection when linked to workflow templates or tasks.
- UI: project management section with create/list/select/update/delete controls.
- Tests: API project tests extended for update/delete/conflict behavior.

Verification:

- `apps/api`: `34 passed`
- `apps/host-runner`: `5 passed`
- `apps/telegram-bot`: `10 passed`
- `apps/ui`: `npm run build` successful
