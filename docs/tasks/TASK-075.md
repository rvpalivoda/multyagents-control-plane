# Task 075: Playwright UI E2E critical journeys

## Metadata
- Status: `in_progress`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-25`
- Updated: `2026-02-25`

## Objective

Add deterministic Playwright browser E2E coverage for critical Runs/Workflows operator journeys.

## Non-goals

- Replace existing UI Vitest smoke tests.
- Add live backend-dependent E2E flows in this task.
- Change Runs/Workflows product behavior outside deterministic test harness support.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Architecture: `docs/ARCHITECTURE.md#10-testing-strategy`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-5-hardening-3-4-days`

## Scope

- Add Playwright configuration for `apps/ui` with CI-friendly defaults:
  - local dev-server bootstrapping
  - deterministic single-worker CI mode
  - retries on CI only
  - machine-readable JSON/JUnit reporters
- Add deterministic E2E mock fixture for control-panel API endpoints used by workflows/runs pages.
- Implement critical journey E2E tests:
  1. create workflow via quick-create
  2. create run and dispatch path visibility
  3. failure triage view + partial rerun flow surface
  4. timeline/cards visibility
- Wire `apps/ui` npm scripts for Playwright execution.
- Update test matrix with new UI E2E command.

## Acceptance criteria
- [x] Implemented with deterministic checks.
- [x] Included in automated test command(s).
- [x] Produces machine-readable evidence.

## Implementation notes

- Added Playwright config: `apps/ui/playwright.config.ts`.
- Added deterministic E2E API mock fixture: `apps/ui/e2e/fixtures/controlPanelApiMock.ts`.
- Added critical-journey suite: `apps/ui/e2e/critical-journeys.spec.ts`.
- Added npm scripts:
  - `cd apps/ui && npm run test:e2e`
  - `cd apps/ui && npm run test:e2e:ci`
- Added ignore patterns for generated Playwright outputs: `.gitignore` (`playwright-report/`, `test-results/`).
- Updated matrix entry: `docs/TEST_MATRIX.md`.

## Test plan

- [ ] `cd apps/ui && npm ci` (failed in sandbox: `esbuild` postinstall EPERM while executing local binary)
- [ ] `cd apps/ui && npm run build` (failed: `vite` missing because `node_modules` install did not complete)
- [ ] `cd apps/ui && npm run test:smoke` (failed: local `vitest` binary missing)
- [ ] `cd apps/ui && npm run test:e2e` (failed: network/DNS blocked for `npx @playwright/test` with `EAI_AGAIN`)
- [ ] `git commit -m "feat(task-075): add playwright ui critical journey coverage"` (failed: git worktree lock path outside writable roots, permission denied)

## Risks and mitigations

- Risk: no live-backend assertions in this suite could mask integration wiring issues.
- Mitigation: fixture covers exact UI API contract shapes for deterministic critical-path confidence; compose/system E2E remains separate gate.
- Risk: `npx` bootstrap for Playwright requires npm registry access in environments without preinstalled package.
- Mitigation: CI image should preinstall dependencies (`npm ci`) before test execution.

## Result

- Implemented deterministic Playwright critical journeys and CI-oriented configuration.
- Validation in this sandbox is environment-blocked by dependency/network constraints (see Test plan).
- Blocker:
  - Git commit is blocked in this sandbox because git worktree metadata is outside writable roots:
    `/home/roman/code/multyagents.dev/.git/worktrees/multyagents-task-075-next/index.lock` (`Permission denied`).
- Unblock options:
  - Run `npm ci`, `npm run build`, `npm run test:smoke`, and `npm run test:e2e` in a host environment with executable install scripts and npm registry access.
  - Run the commit from a host shell where the git worktree metadata path is writable.
- Commits: `<final-sha>`
