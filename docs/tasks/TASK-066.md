# Task 066: E2E Reliability Gate Script

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Add one command that executes release-critical reliability checks across API, Telegram bot, UI, readiness, and optional compose E2E with a clear pass/fail summary.

## Non-goals

- Replacing existing standalone commands (`readiness`, `e2e`, `ui-test-smoke`).
- Expanding scenario coverage beyond current regression and smoke checks.
- Introducing new services, runtime profiles, or execution modes.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#10-testing-strategy`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add `scripts/reliability-gate.sh` to orchestrate required checks in one run.
- Integrate a new `reliability` subcommand into `scripts/multyagents`.
- Make compose E2E step optional through `--with-e2e`.
- Print a final summary table and return non-zero when any executed step fails.
- Update test documentation to include reliability gate commands.

## Acceptance criteria

- [x] One command runs the reliability gate sequence.
- [x] Clear pass/fail summary table is printed.
- [x] Command exits non-zero when any executed step fails.
- [x] `scripts/multyagents` includes `reliability` subcommand.
- [x] `docs/TEST_MATRIX.md` includes reliability gate entries.

## Implementation notes

- Added `scripts/reliability-gate.sh` with six ordered checks:
  1. `apps/api` pytest
  2. `apps/telegram-bot` pytest
  3. `apps/ui` build
  4. `scripts/ui-test-smoke.sh`
  5. `scripts/multyagents readiness`
  6. `scripts/multyagents e2e` (optional via `--with-e2e`)
- Summary table includes check name, status (`PASS`/`FAIL`/`SKIP`), exit code, and executed command.
- `scripts/multyagents reliability` forwards CLI flags directly to the reliability script.

## Test plan

- [x] `bash -n scripts/reliability-gate.sh scripts/multyagents`
- [x] `./scripts/multyagents reliability` (default flow, E2E skipped)
- [x] `./scripts/multyagents reliability --with-e2e` (full flow with E2E)

## Risks and mitigations

- Risk: local dependency/runtime setup can cause false negatives (missing virtualenv, npm packages, Docker availability).
- Mitigation: each step uses explicit command output and summary row with exit code for quick diagnosis.
- Risk: full gate is heavy and slower for local loops.
- Mitigation: E2E is opt-in via `--with-e2e`; default run keeps readiness coverage but skips E2E.

## Blocker

- Blocker: cannot create git commit in this sandbox because git worktree metadata is outside writable roots and lock creation fails (`.../.git/worktrees/multyagents-task-066-next/index.lock: Permission denied`).
- Unblock option 1: run commit from a host environment where `/home/roman/code/multyagents.dev/.git/worktrees/multyagents-task-066-next/` is writable.
- Unblock option 2: move this worktree under a writable gitdir location and commit there.

## Result

Delivered:

- Added one-command reliability gate script and integrated it into `scripts/multyagents`.
- Added optional E2E execution flag and deterministic summary output.
- Updated test matrix with default and full gate command entries.

Validation evidence:

- `bash -n scripts/reliability-gate.sh scripts/multyagents`
- `./scripts/multyagents reliability`
- `./scripts/multyagents reliability --with-e2e`

Observed outputs in this sandbox:

- Syntax check: passed.
- `./scripts/multyagents reliability`: gate summary printed, failed 5/6 executed checks because local deps are missing (`pytest`, `vite`, `fastapi`) and npm registry access is unavailable (`EAI_AGAIN`).
- `./scripts/multyagents reliability --with-e2e`: gate summary printed, failed 6/6 checks; includes host-runner dependency install failure due no package registry access.

- Commits: `<final-sha>`


Verification:
- Implemented `./scripts/multyagents gate` full reliability gate command with pass/fail output.
