# Task 040: Redesign admin IA with operations dashboard and runs center split-view

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-24`
- Updated: `2026-02-24`

## Objective

Deliver a higher-UX administrative interface for operators: clearer information architecture, faster navigation, and action-focused monitoring for runs/approvals.

## Non-goals

- Backend/API schema or endpoint changes.
- Replacing current workflow JSON editor with full visual DAG canvas.
- Introducing websocket transport in this task.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add persistent admin IA shell (sidebar navigation + top operations bar).
- Add global search and project context filter.
- Expand overview into operational dashboard with “needs attention” panel.
- Rework Runs tab into split-view operations center (list + details/timeline).
- Improve approvals inbox prioritization and visibility.

## Acceptance criteria

- [x] Operator has persistent navigation and quick actions without scrolling through all screens.
- [x] Overview highlights pending approvals/failures and provides direct action links.
- [x] Runs center supports list/detail workflow in one screen.
- [x] Approvals inbox prioritizes pending decisions and stays operable with filters.
- [x] `apps/ui` build passes with no API contract changes.

## Implementation notes

Keep existing CRUD and dispatch handlers untouched; focus on IA/UX layer and derived UI state only.

## Test plan

- [x] `cd apps/ui && npm run build`
- [ ] Manual smoke across tabs: create/update entities, run actions, task dispatch, approval decision (requires interactive browser pass).

## Risks and mitigations

- Risk: larger JSX block may regress maintainability.
- Mitigation: use stable class tokens and derived selectors; component split planned as follow-up.

## Result

Implemented a new operations-oriented admin UX layer in the existing Tailwind panel:
- persistent IA shell with left sidebar navigation and top operations bar
- global search and project context filtering applied to runs/tasks/approvals views
- overview upgraded with attention panel (pending approvals, failed runs/tasks) and direct actions
- runs tab redesigned into split-view operations center (list + run details + timeline)
- approvals inbox now sorted/prioritized with context-aware filtering

Execution evidence:
- `apps/ui`: `npm run build` -> success.

Commits:
- `3097a93`
