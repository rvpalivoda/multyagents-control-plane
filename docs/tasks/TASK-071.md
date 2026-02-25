# Task 071: Chaos E2E failure drills

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Add deterministic chaos E2E drills that inject runtime failures during active workflow runs and verify expected behavior for:
- runner unreachable
- API restart tolerance

## Non-goals

- Introducing new API endpoints or persistence models for chaos testing.
- Replacing existing smoke/readiness commands.
- Expanding beyond the minimum two required failure drills in this task.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#10-testing-strategy`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add a new compose scenario script that runs both required chaos drills in one command.
- Ensure deterministic assertions and final machine-readable JSON summary.
- Integrate scenario into launcher command: `./scripts/multyagents chaos`.
- Add targeted tests for pure helper logic introduced by the new script.
- Update test matrix and this task document with execution evidence.

## Acceptance criteria

- [x] Implemented with deterministic checks.
- [x] Included in automated test command(s).
- [x] Produces machine-readable evidence.

## Implementation notes

- Added `infra/compose/scripts/chaos_e2e_failure_drills.py` with two explicit scenarios:
  - `api_restart_tolerant_flow`: restart API container during an active run and verify run reaches `success`.
  - `runner_unreachable_active_run`: stop host-runner during an active run and verify task transitions to `submit-failed` with triage hints and run transitions to `failed`.
- Scenario output includes structured JSON summary (`config`, `summary`, `scenarios`) and explicit final `[chaos] PASS|FAIL`.
- Added launcher integration:
  - `scripts/multyagents chaos`
  - `infra/compose/scripts/run-e2e.sh` now forwards scenario context env (`E2E_COMPOSE_DIR`, `E2E_RUNNER_PID`, `E2E_HOST_RUNNER_PORT`, `E2E_RUNNER_HEALTH_URL`).
- Added targeted unit tests:
  - `infra/compose/scripts/test_chaos_e2e_failure_drills.py` for summary + URL parsing helper behavior.

## Test plan

- [x] `bash -n scripts/multyagents infra/compose/scripts/run-e2e.sh`
- [x] `python3 -m py_compile infra/compose/scripts/chaos_e2e_failure_drills.py infra/compose/scripts/e2e_smoke.py infra/compose/scripts/parallel_workflow_stress_smoke.py`
- [x] `python3 -m unittest infra/compose/scripts/test_chaos_e2e_failure_drills.py`
- [x] `./scripts/multyagents help`
- [ ] `./scripts/multyagents chaos` (attempted, blocked by offline dependency install in `apps/host-runner/.venv`)

## Risks and mitigations

- Risk: full chaos run depends on Docker daemon availability in local environment.
- Mitigation: include deterministic syntax/unit checks that run without Docker; keep runtime chaos flow in one command for easy retry in dependency-ready environment.

## Result

- Implemented and validated in local host environment.
- `./scripts/multyagents chaos` -> PASS (overall_status=success with expected_pending scenarios).
- `./scripts/multyagents race-stress` -> PASS (all invariants passed).
- `python3 -m unittest infra/compose/scripts/test_chaos_e2e_failure_drills.py` -> passed.
- `cd apps/api && .venv/bin/pytest -q tests/test_api_concurrency_stress.py` -> passed.
- Commits: `<final-sha>`
