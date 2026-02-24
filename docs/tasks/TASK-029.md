# Task 029: Add end-to-end smoke test runner for docker stack + host runner

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Provide a reproducible E2E test entrypoint that validates the real local deployment path:
dockerized API/UI/telegram-bot plus host-runner callback loop.

## Non-goals

- Full load/performance testing.
- Browser UI automation (Playwright/Cypress) in this iteration.

## References

- Product spec: `docs/PRODUCT_SPEC.md#6-acceptance-criteria-mvp`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add an executable E2E script that:
  - starts host-runner locally in mock mode
  - starts docker compose stack
  - runs API smoke scenario end-to-end
  - validates task/run completion via callbacks
  - tears down processes
- Add clear operator command to run E2E in one line.
- Add docs with expected ports/envs and failure diagnostics.

## Acceptance criteria

- [x] One command launches and validates end-to-end flow.
- [x] E2E scenario includes workflow template run + dispatch-ready progression.
- [x] Test asserts final workflow run `success`.
- [x] Docs describe prerequisites and usage.

## Implementation notes

Use host-runner `mock` executor to keep E2E deterministic and fast.

## Test plan

- [x] Execute E2E script locally and capture successful output.
- [x] Run existing service tests and UI build after integration.

## Risks and mitigations

- Risk: leftover services/processes after failure.
- Mitigation: strict trap/finally cleanup in launcher script.

## Result

Implemented reproducible E2E smoke pipeline for local stack:

- Added runner script:
  - `infra/compose/scripts/run-e2e.sh`
  - starts host-runner in mock mode on host
  - starts docker compose stack
  - runs E2E scenario
  - always performs cleanup (`docker compose down`, runner stop)
- Added scenario script:
  - `infra/compose/scripts/e2e_smoke.py`
  - validates:
    - API health
    - role creation
    - workflow template creation
    - workflow run creation from template
    - two `dispatch-ready` cycles
    - both tasks reach `success`
    - workflow run reaches `success`
- Updated docs:
  - `infra/compose/README.md` with one-command E2E usage
  - `README.md` with E2E quick-start section

Execution evidence:

- Ran `./scripts/run-e2e.sh` from `infra/compose` successfully.
- Key output:
  - `[e2e] task success: 1`
  - `[e2e] task success: 2`
  - `[e2e] run success: 1`
  - `[e2e] smoke passed`

Post-integration verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `47 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `12 passed`
- `apps/ui`: `npm run build` successful

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
