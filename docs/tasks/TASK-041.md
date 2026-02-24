# Task 041: Refactor admin UI into modular React components

## Metadata

- Status: `in_progress`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-24`
- Updated: `2026-02-24`

## Objective

Improve maintainability and delivery speed of the admin panel by decomposing `App.tsx` into focused React components while preserving current UX and behavior.

## Non-goals

- API contract changes.
- Visual redesign of already delivered UX.
- Rewriting all tabs in one pass.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Extract shared UI types/constants into dedicated module.
- Extract shell components (sidebar/topbar) from `App.tsx`.
- Extract high-complexity sections (`overview`, `runs`, `approvals`) into standalone files.
- Keep existing handlers/state in `App.tsx` and pass props explicitly.

## Acceptance criteria

- [ ] `App.tsx` becomes smaller and easier to navigate.
- [ ] Extracted components compile with strict TypeScript checks.
- [ ] Behavior of runs/approvals/dashboard remains unchanged.
- [ ] `apps/ui` build passes.

## Implementation notes

Prefer explicit prop contracts over implicit context to keep boundaries clear.

## Test plan

- [ ] `cd apps/ui && npm run build`
- [ ] Manual smoke: sidebar/topbar navigation, runs center actions, approval decisions.

## Risks and mitigations

- Risk: prop wiring regression in extracted sections.
- Mitigation: keep functional handlers in `App.tsx` and avoid behavioral edits during extraction.

## Result

To be filled after implementation.

Commits:
- `TBD`
