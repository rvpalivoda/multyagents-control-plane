# Task 062: Runbooks for Local Failure Recovery

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Document and standardize recovery flow for common local operational failures.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#9-deployment-topology`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Runner offline playbook.
- Stuck queued/running playbook.
- Worktree conflict cleanup playbook.

## Acceptance criteria

- [x] Added runbook docs for runner offline, stuck queued/running, and worktree conflict cleanup.
- [x] Each runbook contains quick command snippets and decision-tree style flow.
- [x] Runbooks are linked from the main docs index and root README.
- [x] Task document contains implementation and verification evidence.

## Test plan

- [x] Validate runbook links and paths with `rg`.
- [x] Validate command surface against launcher help (`./scripts/multyagents help`).

## Result

- Delivered:
  - Added `docs/README.md` as main docs index.
  - Added runbooks:
    - `docs/runbooks/RUNNER_OFFLINE.md`
    - `docs/runbooks/STUCK_QUEUED_RUNNING.md`
    - `docs/runbooks/WORKTREE_CONFLICT_CLEANUP.md`
  - Updated root `README.md` with documentation/runbook links.
- Verification evidence:
  - `rg -n "docs/README.md|RUNNER_OFFLINE|STUCK_QUEUED_RUNNING|WORKTREE_CONFLICT_CLEANUP" README.md docs/README.md -S` -> paths linked.
  - `./scripts/multyagents help` -> launcher command surface confirmed.
- Commit evidence: blocked in this environment (see blocker section).

## Blocker

- Cannot create git commit in this sandboxed worktree:
  - `fatal: Unable to create '/home/roman/code/multyagents.dev/.git/worktrees/multyagents-task-062/index.lock': Permission denied`
- Unblock options:
  1. Run commit from an environment with write access to the parent `.git/worktrees/*` path.
  2. Re-open this task with sandbox permissions that allow git metadata writes.
