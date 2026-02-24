# Task 038: Migrate UI to Tailwind and deliver full-width modern admin layout

## Metadata

- Status: `done`
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

- [x] UI builds successfully with Tailwind enabled.
- [x] Main layout uses full screen width and modern admin visual structure.
- [x] Existing core actions (project/role/workflow/task/run/approval) remain available.
- [x] No API endpoint changes are required for this UI update.

## Implementation notes

Prefer incremental migration in `App.tsx` to avoid behavior regressions.

## Test plan

- [x] `cd apps/ui && npm run build`
- [x] Manual smoke: tab navigation + at least one action per core section.

## Risks and mitigations

- Risk: visual refactor can break form usability.
- Mitigation: keep labels/actions explicit and preserve control grouping by domain.

## Result

Tailwind CSS was integrated into the Vite React app and the control panel was migrated to a modern full-width admin layout.

Delivered behavior:
- full-width dashboard shell with metrics cards and tab navigation
- modernized forms/tables/JSON panes using consistent Tailwind classes
- preserved API-driven flows for projects, roles, skill packs, workflows, runs, tasks, and approvals
- approvals inbox actions (lookup/approve/reject) retained in the new layout

Execution evidence:
- `apps/ui`: `npm run build` -> success

Commits:
- `273f808`
