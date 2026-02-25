# Task 047: Parallel Worktree Session Manager

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Improve isolated worktree safety for parallel agent execution with explicit session mapping, collision safeguards, and deterministic cleanup behavior.

## Non-goals

- Automatic merge to protected branches.
- Full persistent DB migration beyond in-memory snapshot fields.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#5-execution-modes`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-4-git-and-isolation-4-5-days`

## Scope

- Run-aware isolated naming (`run-<id>` + `task-<id>`) for branch/worktree.
- Explicit mapping in audit: `task_run_id`, `workflow_run_id`, `worktree_path`, `git_branch`.
- Session reservation/release lifecycle in API for dispatch/submit-fail/terminal/cancel.
- Host-runner collision checks for reserved branch/worktree.
- Host-runner cleanup telemetry for isolated tasks.

## Acceptance criteria

- [x] Parallel isolated tasks use unique run-scoped worktree/branch mapping.
- [x] Cleanup path is executed for success/failure/cancel and emitted in status/audit fields.
- [x] UI can show worktree/branch via task audit payload (audit JSON panel).

## Implementation notes

- API `InMemoryStore` now reserves isolated sessions and emits:
  - `task.worktree_session_reserved`
  - `task.worktree_session_released`
- Audit model extended with task-run and cleanup metadata.
- Runner payload now carries real workflow run id when present.
- Host-runner now:
  - reserves isolated session at submit,
  - checks `git worktree list --porcelain` for branch/path collision before `worktree add`,
  - reports cleanup outcome in status callback payload.

## Test plan

- [x] API tests for run-aware mapping and isolated collision guards.
- [x] Host-runner tests for cleanup on failure/cancel and submit collision rejection.
- [x] Full targeted pytest execution in local environment.

## Risks and mitigations

- Risk: delayed runner callback may arrive after API released session on cancel.
- Mitigation: release operation is idempotent and audit cleanup fields are still updated from callback.

- Risk: stale git state outside runner reservation map.
- Mitigation: runner validates branch/path conflicts from `git worktree list` before setup.

## Result

- Added task-run worktree session mapping and cleanup audit surface across API/runner.
- Added collision safeguards in API reservation and host-runner submit/setup paths.
- Added/updated API and host-runner tests for mapping, cleanup, and collision scenarios.
- Verification:
  - `python3 -m py_compile ...` for changed API/runner/test modules (pass).
  - `apps/api`: `pytest -q tests/test_api_cancel.py tests/test_api_context7.py tests/test_api_runner_status.py` -> passed (18).
  - `apps/host-runner`: `pytest -q tests/test_runner_api.py` -> passed (15).
- Commits:
  - `f99b17f`
