# Task 013: Integration tests for one code workflow and one text workflow

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Add end-to-end integration tests that validate one coding flow and one text flow through current API orchestration.

## Non-goals

- Running real `codex` process and real git side effects.
- Multi-service full-stack tests with external Telegram API.

## References

- Product spec: `docs/PRODUCT_SPEC.md#6-acceptance-criteria-mvp`
- Architecture: `docs/ARCHITECTURE.md#10-testing-strategy`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Code workflow integration test:
  - project + role + workflow template + shared-workspace task + run + dispatch
  - verify payload/audit/events
- Text workflow integration test:
  - no-workspace task + approval gate + approval decision + dispatch
  - verify payload/audit/events

## Acceptance criteria

- [x] At least one code workflow integration test passes.
- [x] At least one text workflow integration test passes.
- [x] Tests validate lifecycle outputs (dispatch payload, audit, timeline events).

## Implementation notes

Use API TestClient integration style with in-memory store state.

## Test plan

- [x] Add integration test module in `apps/api/tests`.
- [x] Run full API pytest suite.

## Risks and mitigations

- Risk: coupling to global in-memory state can make tests flaky.
- Mitigation: use unique entities per test and avoid fixed assumptions on global counts.

## Result

Implemented:
- Added `apps/api/tests/test_integration_workflows.py` with two end-to-end API scenarios:
  - code workflow with shared workspace, workflow run, dispatch, audit, and timeline assertions
  - text workflow with approval gate, blocked dispatch, approval decision, dispatch, audit, and timeline assertions
- Reused current orchestration endpoints to validate integrated behavior across tasks, runs, approvals, and events.

Verification:
- `apps/api`: `./.venv/bin/pytest -q` -> `31 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `4 passed`
- `apps/ui`: `npm run build` succeeded

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
