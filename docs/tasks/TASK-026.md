# Task 026: Implement isolated-worktree mode with git worktree lifecycle

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Deliver real `isolated-worktree` execution so tasks run in dedicated git worktrees instead of shared project root.

## Non-goals

- Merge automation to protected branches.
- Advanced branch naming policies across teams.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-agent-execution-modes`
- Architecture: `docs/ARCHITECTURE.md#5-execution-modes`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-4-git-and-isolation-4-5-days`

## Scope

- Require `project_id` for `isolated-worktree` tasks.
- Extend runner workspace payload with optional `worktree_path` and `git_branch`.
- API dispatch for isolated mode builds dedicated worktree metadata.
- Host-runner creates git worktree before execution and cleans it after completion.
- Add tests for API payload and runner git lifecycle behavior.

## Acceptance criteria

- [x] `isolated-worktree` task validation enforces project binding.
- [x] Dispatch payload contains isolated workspace metadata.
- [x] Host-runner performs `git worktree add` before execution and cleanup after.
- [x] Tests validate isolated-worktree flow.

## Implementation notes

Use deterministic branch/worktree naming for MVP:
- branch: `multyagents/task-{task_id}`
- path: `<project_root>/.multyagents/worktrees/task-{task_id}`

## Test plan

- [x] API tests for isolated-worktree validation and payload.
- [x] Host-runner tests for worktree setup/cleanup commands.
- [x] Full regressions and UI build.

## Risks and mitigations

- Risk: cleanup may fail due to repo state.
- Mitigation: force remove and keep explicit stderr in runner metadata.

## Result

Implemented `isolated-worktree` execution lifecycle end-to-end:

- API validation:
  - `TaskCreate` now requires `project_id` for `execution_mode=isolated-worktree`.
- API dispatch workspace payload:
  - includes deterministic worktree metadata:
    - `worktree_path`: `<project_root>/.multyagents/worktrees/task-{task_id}`
    - `git_branch`: `multyagents/task-{task_id}`
- Host-runner workspace schema extended with:
  - `worktree_path`
  - `git_branch`
- Host-runner `isolated-worktree` runtime behavior:
  - setup: `git worktree add --force -B <branch> <path> HEAD`
  - execute in worktree cwd
  - cleanup: `git worktree remove --force <path>`
  - cleanup toggle via `HOST_RUNNER_CLEANUP_WORKTREE=false`
- Runner client now forwards worktree metadata in submit payload.
- Shared contracts schema updated to allow workspace fields used by isolated mode.

Tests added/updated:

- `apps/api/tests/test_api_context7.py`
  - isolated mode requires project id
  - isolated dispatch includes worktree metadata
- `apps/host-runner/tests/test_runner_api.py`
  - validates worktree add/execute/remove command sequence
  - validates isolated payload metadata requirement

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `43 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `12 passed`
- `apps/ui`: `npm run build` successful

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
