# Task 017: Extend role model with prompts/tools/skill packs/constraints

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Bring role configuration closer to product spec by adding prompt/tool/skills/constraints fields managed from UI and API.

## Non-goals

- Full policy engine enforcement for each field.
- External skill registry sync.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#7-security-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Extend role schema (`create/read/update`) with:
  - `system_prompt`
  - `allowed_tools`
  - `skill_packs`
  - `execution_constraints`
- Persist fields in API store and include in CRUD responses.
- Add UI controls for these fields in role form.
- Update shared contracts and tests.

## Acceptance criteria

- [x] Role API accepts and returns new policy fields.
- [x] UI can create/update role with new policy fields.
- [x] API tests cover persistence of added role fields.
- [x] Existing tests remain green.

## Implementation notes

Use normalized list handling (trim + deduplicate) for tools/skills.
Store `execution_constraints` as JSON object for flexibility.

## Test plan

- [x] Extend role API tests for new fields.
- [x] Run full API test suite and UI build.

## Risks and mitigations

- Risk: invalid constraints JSON from UI.
- Mitigation: parse on client and show explicit error.

## Result

Implemented:
- Extended role API models (`create/read/update`) with:
  - `system_prompt`
  - `allowed_tools`
  - `skill_packs`
  - `execution_constraints`
- Added normalization for role tool/skill lists (trim + deduplicate).
- Updated in-memory store persistence and role CRUD responses for new fields.
- Updated UI role management section with inputs for:
  - system prompt
  - allowed tools
  - skill packs
  - execution constraints JSON
- Updated shared contracts for expanded `RoleRead`.
- Extended API role tests to validate field persistence and normalization.

Verification:
- `apps/api`: `./.venv/bin/pytest -q` -> `31 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `4 passed`
- `apps/ui`: `npm run build` succeeded
