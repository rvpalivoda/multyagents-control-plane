# Task 037: Improve control-panel UX navigation and approvals workflow

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-24`
- Updated: `2026-02-24`

## Objective

Make the web control panel easier to operate by reducing on-screen clutter, adding focused tab navigation, and exposing first-class approval decision actions from UI.

## Non-goals

- Full visual redesign with external component library.
- Real-time websocket streaming.
- Backend/API schema changes for approvals.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add tab-based navigation in the existing React control panel.
- Add dashboard counters and refresh-all action.
- Add run/task search filters for faster navigation.
- Add approvals inbox section with lookup, approve/reject actions, and actor/comment payload support.
- Add role selector in task creation flow.

## Acceptance criteria

- [x] Operator can switch between focused UI tabs instead of a single long page.
- [x] Operator can find runs/tasks via search inputs.
- [x] Operator can load approvals and submit approve/reject decisions from the panel.
- [x] Existing CRUD/dispatch flows continue to work.

## Implementation notes

Kept API integration centralized in `App.tsx` and introduced explicit API error status handling to support safe 404 fallback for missing approvals.

## Test plan

- [x] UI build check: `cd apps/ui && npm run build`
- [x] Manual sanity: verify create/update flows remain reachable in tabbed layout.

## Risks and mitigations

- Risk: hidden-tab layout may hide errors from operators.
- Mitigation: keep global error banner visible above all tabs.

## Result

Implemented focused, tab-based control panel navigation and added approvals inbox operations without changing backend contracts.

Execution evidence:
- `apps/ui`: `npm run build` -> success.

Commits:
- `d622e07`
