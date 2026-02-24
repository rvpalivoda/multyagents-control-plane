# Task 036: Implement skill-pack management in API and UI

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-24`

## Objective

Provide full operator flow to manage skill-packs and attach them to roles from control panel.

## Non-goals

- External marketplace of community skills.
- Automatic skill quality ranking.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#3-main-data-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add `skill_pack` model and CRUD API endpoints.
- Validate included skills against local skills catalog.
- Extend role forms/API to bind/unbind skill-packs.
- Add UI page for skill-pack list/create/edit/delete and role assignment view.

## Acceptance criteria

- [x] Operator can CRUD skill-packs from UI.
- [x] Role can reference one or more skill-packs with backend validation.
- [x] API returns clear errors for unknown/duplicate skills or pack names.
- [x] UI displays which roles use each skill-pack.

## Implementation notes

Read catalog from `docs/SKILLS_CATALOG.md` initially; move to dedicated registry API later if needed.

Execution lane:
- Lane C in `docs/EXECUTION_BOARD.md` (parallel implementation track).

## Test plan

- [x] API tests for skill-pack CRUD and role-assignment validation.
- [x] UI tests for create/edit/delete flows.
- [x] Integration test for workflow dispatch payload including resolved skill-packs.

## Risks and mitigations

- Risk: Catalog drift between documentation and runtime.
- Mitigation: Add checksum/version field and validation warning on startup.

## Result

Implemented `skill_pack` management in API and UI:

- Added API entity and CRUD endpoints for skill packs (`/skill-packs`).
- Added catalog-based skill validation from `docs/SKILLS_CATALOG.md`.
- Added role validation so `role.skill_packs` must reference existing packs.
- Added UI section for skill-pack CRUD and role usage visibility.

Execution evidence:

- `apps/api`: `pytest -q` -> `66 passed`.
- `apps/ui`: `npm run build` -> success.

Commits:
- `79be420` (`feat(task-036): add skill-pack api and ui management`)
- `a2709ce` (`feat(task-036): include role skill packs in dispatch payload`)
- `5c4324c` (`fix(task-036): make skills catalog lookup container-safe`)
