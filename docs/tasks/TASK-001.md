# Task 001: Establish project control process and task governance

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Define and commit the minimum operating process to keep development under control:
- unified task lifecycle
- mandatory task template
- backlog entry point
- stack decision recorded as ADR

## Non-goals

- Implement runtime services or business features.
- Build UI/API code for orchestration.

## References

- Product spec: `docs/PRODUCT_SPEC.md#1-product-intent`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Add `docs/DEVELOPMENT_PROCESS.md`
- Add `docs/templates/TASK_TEMPLATE.md`
- Add `docs/BACKLOG.md`
- Add ADR for Python-only baseline
- Update governance rules in `AGENTS.md`

## Acceptance criteria

- [x] Task lifecycle and state transitions documented.
- [x] Task template exists and is reusable.
- [x] Backlog file with initial epics/tasks exists.
- [x] Python-only v0.1 decision fixed as ADR.
- [x] `AGENTS.md` references process docs and task governance.

## Implementation notes

Implemented docs-first governance. Chose lightweight markdown process (no heavy external tracker) to keep local personal workflow fast and transparent.

## Test plan

- [x] Manual validation: verify files exist and are readable.
- [x] Manual validation: verify references in `AGENTS.md` are consistent.

## Risks and mitigations

- Risk: process docs may drift from real execution.
- Mitigation: enforce task updates in every feature task and weekly backlog review.

## Result

Created:
- `docs/DEVELOPMENT_PROCESS.md`
- `docs/templates/TASK_TEMPLATE.md`
- `docs/BACKLOG.md`
- `docs/adr/0001-python-only-v0-1.md`

Updated:
- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/IMPLEMENTATION_PLAN.md`
