# Task 030: Add one-command local launcher for full stack lifecycle

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Provide a single command entrypoint to manage the full local environment:
host-runner + docker compose services + health/status visibility.

## Non-goals

- Electron desktop packaging in this iteration.
- Production deployment orchestration.

## References

- Product spec: `docs/PRODUCT_SPEC.md#1-product-intent`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Add root launcher script with subcommands:
  - `up`
  - `down`
  - `status`
  - `logs`
  - `e2e`
- `up`:
  - ensure host-runner venv/runtime
  - start host-runner in background
  - start compose stack
  - verify health endpoints
- `down`:
  - stop compose stack
  - stop host-runner by pid file
- Update docs with one-command usage and defaults.

## Acceptance criteria

- [x] `./scripts/multyagents up` starts full stack.
- [x] `./scripts/multyagents down` cleanly stops everything.
- [x] `./scripts/multyagents status` reports services state.
- [x] Docs describe launcher usage.

## Implementation notes

Use `.multyagents-runtime/` for pid/log files to avoid polluting app directories.

## Test plan

- [x] Run `up -> status -> down`.
- [x] Run `e2e` via launcher wrapper.
- [x] Run existing regressions and UI build.

## Risks and mitigations

- Risk: stale pid file after crash.
- Mitigation: script verifies process existence before trusting pid file.

## Result

Implemented unified launcher command for full local lifecycle:

- Added root executable:
  - `scripts/multyagents`
- Supported commands:
  - `up`: start host-runner + compose stack + health checks
  - `down`: stop compose + host-runner
  - `status`: process/container + health summary
  - `logs`: host-runner and compose logs tail
  - `e2e`: run end-to-end smoke via existing wrapper
- Runtime state files:
  - `.multyagents-runtime/host-runner.pid`
  - `.multyagents-runtime/host-runner.log`
- Host-runner launch is detached (`nohup`) to survive launcher process exit.
- Added runtime ignore:
  - `.multyagents-runtime/` in `.gitignore`
- Docs updated:
  - `README.md` one-command launcher usage
  - `infra/compose/README.md` launcher as preferred entrypoint

Execution evidence:

- `./scripts/multyagents up` -> stack started successfully (`api/ui/telegram/runner`).
- `./scripts/multyagents status` -> reported running services and healthy endpoints.
- `./scripts/multyagents down` -> cleaned up compose + host-runner.
- `./scripts/multyagents e2e` -> `smoke passed` with workflow run `success`.

Post-change regression:

- `apps/api`: `./.venv/bin/pytest -q` -> `47 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `12 passed`
- `apps/ui`: `npm run build` successful
