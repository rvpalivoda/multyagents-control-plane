# Task 073: Restart persistence invariant tests

## Metadata
- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Validate state integrity across API restarts and callback replay.

## Non-goals

- Add new API endpoints for persistence-specific testing.
- Change runner callback contract semantics.
- Replace existing stress/chaos suites.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#10-testing-strategy`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add a deterministic restart persistence invariant suite in API domain code.
- Validate callback replay behavior after state reload from disk.
- Enforce explicit invariants:
  - no illegal statuses
  - no duplicate dispatch events
  - state recoverability after restart checkpoints
- Add machine-readable evidence generation (JSON + Markdown).
- Add one-command launcher integration for TASK-073.
- Add targeted API regression tests for suite output/invariants.
- Update test matrix and evidence directory docs.

## Acceptance criteria

- [x] Implemented with deterministic checks.
- [x] Included in automated test command(s).
- [x] Produces machine-readable evidence.

## Implementation notes

- Added `multyagents_api.restart_persistence` with:
  - `RestartPersistenceConfig`
  - `run_restart_persistence_invariant_suite`
  - scenario `restart-callback-replay` with restart checkpoints and success callback replay loop
  - invariant report payloads (`id`, `description`, `expected`, `actual`, `passed`).
- Added evidence script `apps/api/scripts/task_073_restart_persistence.py` to emit machine-readable JSON and operator-readable Markdown.
- Added launcher script `scripts/task-073-restart-persistence.sh`:
  - runs suite and writes timestamped artifacts
  - runs targeted pytest
  - updates `latest.json`, `latest.md`, `latest-pytest.log`.
- Added launcher command integration:
  - `./scripts/multyagents restart-persistence`
  - alias `./scripts/multyagents persistence-restart`.
- Added generated-evidence ignore patterns and `docs/evidence/task-073/README.md`.

## Test plan

- [x] `bash -n scripts/multyagents scripts/task-073-restart-persistence.sh`
- [x] `python3 -m py_compile apps/api/src/multyagents_api/restart_persistence.py apps/api/scripts/task_073_restart_persistence.py apps/api/tests/test_api_restart_persistence.py`
- [ ] `cd apps/api && PYTHONPATH=src python3 -m pytest -q tests/test_api_restart_persistence.py` (blocked: `No module named pytest`)
- [ ] `./scripts/multyagents restart-persistence` (blocked: missing dependency `pydantic` in local python env)

## Risks and mitigations

- Risk: local machines without API dependencies cannot execute the suite.
- Mitigation: scripts print deterministic setup guidance and still allow static syntax checks in offline environments.

## Result

- Implemented and validated in local host environment.
- `cd apps/api && .venv/bin/pytest -q tests/test_api_restart_persistence.py tests/test_api_security_adversarial.py` -> passed (9).
- `./scripts/multyagents restart-persistence` -> passed (invariants: 3/3).
- Commits: `<final-sha>`
