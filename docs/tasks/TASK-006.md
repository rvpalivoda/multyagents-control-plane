# Task 006: Implement workflow DAG CRUD from UI

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Implement workflow template CRUD with DAG validation in API and provide UI controls for creating/updating/deleting workflows.

## Non-goals

- Visual graph editor component (React Flow) at this stage.
- Workflow run execution engine changes beyond template CRUD.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add workflow template schemas and CRUD endpoints.
- Validate DAG: unique step ids, dependency existence, acyclic graph.
- Add UI section for workflow CRUD operations.

## Acceptance criteria

- [x] API supports workflow template create/get/list/update/delete.
- [x] Invalid DAG payloads are rejected.
- [x] UI can create, view, update, and delete workflows.
- [x] API tests and UI build pass.

## Implementation notes

Use JSON-based step editor in UI for speed; keep API contracts explicit for later visual DAG editor migration.

## Test plan

- [x] API tests for valid and invalid DAG scenarios.
- [x] UI build check after workflow CRUD controls are added.

## Risks and mitigations

- Risk: DAG validation gaps could allow broken workflows.
- Mitigation: enforce dependency and cycle checks server-side.

## Result

Implemented:
- Added workflow template API schemas and DAG validation rules.
- Added workflow template endpoints:
  - `POST /workflow-templates`
  - `GET /workflow-templates`
  - `GET /workflow-templates/{id}`
  - `PUT /workflow-templates/{id}`
  - `DELETE /workflow-templates/{id}`
- Added server-side validation for:
  - unique `step_id`
  - dependency existence
  - acyclic graph
- Added UI workflow section with JSON-based step editor and CRUD controls.

Verification:
- `apps/api`: `pytest` -> `17 passed`
- `apps/ui`: `npm run build` succeeded
