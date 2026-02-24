# Task 004: Implement project CRUD and local path policy

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Add project CRUD capabilities in API with strict local filesystem path policy (`root_path`, `allowed_paths`) for future agent execution safety.

## Non-goals

- Real filesystem scanning or permission mutation.
- UI full projects page implementation.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#7-security-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add API models for project create/read/list.
- Validate absolute root path.
- Validate each allowed path is absolute and under project root.
- Add tests for valid and invalid path policy scenarios.

## Acceptance criteria

- [x] `POST /projects` creates a project with policy fields.
- [x] `GET /projects` lists created projects.
- [x] `GET /projects/{id}` returns project details.
- [x] Invalid path policy requests are rejected with 422.

## Implementation notes

Use in-memory persistence consistent with current API scaffold, with strict Pydantic validation for policy rules.

## Test plan

- [x] API tests for create/list/get projects.
- [x] API tests for invalid path policy rejections.

## Risks and mitigations

- Risk: path policy validation edge cases.
- Mitigation: use normalized resolved paths and explicit parent checks.

## Result

Implemented:
- Added `ProjectCreate` / `ProjectRead` schemas with strict path policy validation.
- Added API endpoints:
  - `POST /projects`
  - `GET /projects`
  - `GET /projects/{project_id}`
- Added in-memory persistence for projects in store layer.
- Added API tests for valid and invalid path policy scenarios.

Verification:
- `apps/api`: `pytest` -> `11 passed`
