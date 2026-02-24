# Task 039: Switch admin panel to light theme and polish readability

## Metadata

- Status: `in_progress`
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

- [ ] App uses light background with readable contrast across all sections.
- [ ] Forms/tables/action buttons remain usable and visually consistent.
- [ ] No behavior regressions in CRUD/run/task/approval actions.
- [ ] UI build passes.

## Implementation notes

Perform class-token level migration first, then adjust local exceptions.

## Test plan

- [ ] `cd apps/ui && npm run build`
- [ ] Manual smoke: verify each tab remains legible and operable.

## Risks and mitigations

- Risk: contrast regression in selected/hover states.
- Mitigation: use explicit `bg-blue-50` and `hover:bg-slate-50` for rows.

## Result

To be filled after implementation.

Commits:
- `TBD`
