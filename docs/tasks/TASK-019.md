# Task 019: Add API state snapshot persistence for restart resilience

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Persist API in-memory state to disk so tasks/runs/events survive process restart in local mode.

## Non-goals

- Full relational database migration.
- Multi-node distributed consistency.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#10-testing-strategy`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add optional state file path configuration for API store.
- Persist key entities and sequence counters after mutating operations.
- Load saved snapshot on API startup.
- Add tests for save/load behavior.

## Acceptance criteria

- [x] State file is written after mutations when configured.
- [x] API store restores entities from snapshot on initialization.
- [x] Tests validate restart restore behavior.

## Implementation notes

Use atomic write pattern (`tmp` then `replace`) to reduce corruption risk.

## Test plan

- [x] Add store-level persistence test using temp path.
- [x] Run full API and service regression tests.

## Risks and mitigations

- Risk: large snapshots for long-running instances.
- Mitigation: keep scope local MVP and move to DB in later phase.

## Result

Implemented:
- Added optional store state file support in `InMemoryStore(state_file=...)`.
- Added snapshot save/load mechanics for core state:
  - projects, roles, tasks, workflow templates, workflow runs, approvals
  - locks, audits, events
  - sequence counters
- Added atomic snapshot write strategy (`.tmp` + replace).
- Wired API startup to env var:
  - `API_STATE_FILE` in `apps/api/src/multyagents_api/main.py`
- Added persistence test:
  - `apps/api/tests/test_store_persistence.py`
- Updated API README with snapshot persistence configuration.

Verification:
- `apps/api`: `./.venv/bin/pytest -q` -> `32 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `5 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/ui`: `npm run build` succeeded
