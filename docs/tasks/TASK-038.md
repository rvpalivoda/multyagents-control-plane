# Task 038: Migrate UI to Tailwind and deliver full-width modern admin layout

## Metadata

- Status: `in_progress`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-24`
- Updated: `2026-02-24`

## Objective

Upgrade the control panel visual layer to Tailwind CSS and provide a modern full-width administrative layout with improved navigation ergonomics.

## Non-goals

- Backend API contract changes.
- Replacing current data model or business workflows.
- Introducing external paid UI kits.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add Tailwind CSS toolchain into `apps/ui` (Vite + React).
- Migrate the current control panel to Tailwind utility classes.
- Keep tab-based navigation and move to full-width layout.
- Preserve existing CRUD/run/approval capabilities.

## Acceptance criteria

- [ ] UI builds successfully with Tailwind enabled.
- [ ] Main layout uses full screen width and modern admin visual structure.
- [ ] Existing core actions (project/role/workflow/task/run/approval) remain available.
- [ ] No API endpoint changes are required for this UI update.

## Implementation notes

Prefer incremental migration in `App.tsx` to avoid behavior regressions.

## Test plan

- [ ] `cd apps/ui && npm run build`
- [ ] Manual smoke: tab navigation + at least one action per core section.

## Risks and mitigations

- Risk: visual refactor can break form usability.
- Mitigation: keep labels/actions explicit and preserve control grouping by domain.

## Result

To be filled after implementation.

Commits:
- `TBD`
