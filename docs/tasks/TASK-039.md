# Task 039: Switch admin panel to light theme and polish readability

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-24`
- Updated: `2026-02-24`

## Objective

Deliver a light visual theme for the full-width Tailwind admin panel and improve text contrast/readability in tables, forms, and JSON blocks.

## Non-goals

- Functional API changes.
- New domain screens.
- Theme switcher implementation (dark/light toggle).

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Convert global UI shell to light palette.
- Update reusable Tailwind class tokens for controls and tables.
- Keep current tab-based IA and all existing operator actions.
- Verify build and core interaction visibility.

## Acceptance criteria

- [x] App uses light background with readable contrast across all sections.
- [x] Forms/tables/action buttons remain usable and visually consistent.
- [x] No behavior regressions in CRUD/run/task/approval actions.
- [x] UI build passes.

## Implementation notes

Perform class-token level migration first, then adjust local exceptions.

## Test plan

- [x] `cd apps/ui && npm run build`
- [x] Manual smoke: verify each tab remains legible and operable.

## Risks and mitigations

- Risk: contrast regression in selected/hover states.
- Mitigation: use explicit `bg-blue-50` and `hover:bg-slate-50` for rows.

## Result

Updated the Tailwind admin panel to a full light theme with improved readability:
- global shell and surface colors moved to light palette
- form controls/tables/row hover and selected states adapted for light mode
- JSON/debug panes switched to neutral light backgrounds while preserving density
- all existing tab flows and operator actions preserved

Execution evidence:
- `apps/ui`: `npm run build` -> success

Commits:
- `d3e9d03`
