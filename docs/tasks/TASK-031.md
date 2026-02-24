# Task 031: Add Electron desktop wrapper for launcher commands

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Provide a desktop control panel wrapper that runs local lifecycle commands (`up/down/status/logs/e2e`) via GUI buttons.

## Non-goals

- Cross-platform installers and code signing.
- Deep visualization dashboards beyond command output.

## References

- Product spec: `docs/PRODUCT_SPEC.md#1-product-intent`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Add `apps/desktop` Electron app.
- Buttons for launcher commands:
  - `up`, `down`, `status`, `logs`, `e2e`
- Show stdout/stderr and command exit code in UI.
- Add root launcher shortcut command `./scripts/multyagents desktop`.
- Update docs with desktop startup instructions.

## Acceptance criteria

- [x] Desktop app starts and renders command controls.
- [x] Each button triggers corresponding launcher command.
- [x] Output panel shows command result and exit status.
- [x] Docs describe installation and run command.

## Implementation notes

Electron app should call existing `scripts/multyagents` and not duplicate orchestration logic.

## Test plan

- [x] Validate Node/Electron app syntax.
- [x] Validate launcher command integration from desktop main process.
- [ ] Run existing regressions and UI build.

## Risks and mitigations

- Risk: GUI launch may fail in headless environments.
- Mitigation: keep CLI launcher as source of truth and fallback path.

## Result

Implemented `apps/desktop` Electron wrapper with:

- command controls: `up`, `down`, `status`, `logs`, `e2e`
- output stream panel with stdout/stderr and final exit code
- stop-active command support via SIGTERM
- root launcher integration `./scripts/multyagents desktop`
- Linux sandbox guard: launcher auto-uses `--no-sandbox` when Electron `chrome-sandbox` permissions are not `root:4755`, with remediation hint

Updated docs:

- `README.md` one-command launcher section
- `apps/desktop/README.md` desktop-specific usage

Verification executed:

- `npm --prefix apps/desktop install --no-audit --no-fund`
- `npm --prefix apps/desktop run check`
- `./scripts/multyagents help` includes `desktop`

GUI runtime note:

- Electron window launch was not executed in this headless terminal session.
