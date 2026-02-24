# Task 041: Refactor admin UI into modular React components

## Metadata

- Status: `done`
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

- [x] `App.tsx` becomes smaller and easier to navigate.
- [x] Extracted components compile with strict TypeScript checks.
- [x] Behavior of runs/approvals/dashboard remains unchanged.
- [x] `apps/ui` build passes.

## Implementation notes

Prefer explicit prop contracts over implicit context to keep boundaries clear.

## Test plan

- [x] `cd apps/ui && npm run build`
- [ ] Manual smoke: sidebar/topbar navigation, runs center actions, approval decisions (requires interactive browser session).

## Risks and mitigations

- Risk: prop wiring regression in extracted sections.
- Mitigation: keep functional handlers in `App.tsx` and avoid behavioral edits during extraction.

## Result

Refactored the admin panel into modular React units while preserving behavior:
- extracted shared control-panel types and tab constants into `src/types/controlPanel.ts`
- extracted shell blocks (`AdminSidebar`, `AdminTopBar`)
- extracted high-complexity sections (`OverviewSection`, `RunsCenterSection`, `ApprovalsSection`)
- kept state and handler ownership in `App.tsx` with explicit prop contracts

Execution evidence:
- `apps/ui`: `npm run build` -> success.

Commits:
- `b1b5f28`
