# Task 005: Implement role CRUD from UI

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Implement full role lifecycle (create/read/list/update/delete) and expose controls in UI.

## Non-goals

- Fine-grained role permission editor.
- Bulk role operations.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#3-main-data-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add API endpoints for list/update/delete roles.
- Protect role deletion when tasks reference the role.
- Add UI controls for listing, editing, and deleting roles.

## Acceptance criteria

- [x] API supports role create/get/list/update/delete.
- [x] Deleting a role with attached tasks returns conflict.
- [x] UI can create, view, update, and delete roles.
- [x] API and UI checks pass.

## Implementation notes

Keep role model minimal (`name`, `context7_enabled`) while enabling safe lifecycle operations.

## Test plan

- [x] API tests for list/update/delete and conflict path.
- [x] UI build check after CRUD controls added.

## Risks and mitigations

- Risk: role deletion may break existing tasks.
- Mitigation: enforce API conflict when role has linked tasks.

## Result

Implemented:
- Added role API endpoints:
  - `GET /roles`
  - `PUT /roles/{role_id}`
  - `DELETE /roles/{role_id}`
- Added conflict protection for role deletion when linked tasks exist (`409`).
- Extended UI role section with:
  - role list
  - select/edit role
  - delete role
  - refresh action

Verification:
- `apps/api`: `pytest` -> `13 passed`
- `apps/ui`: `npm run build` succeeded
