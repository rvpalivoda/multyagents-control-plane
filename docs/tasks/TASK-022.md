# Task 022: Add native codex executor mode in host-runner

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Provide a first-class `codex` executor in host-runner that invokes local `codex exec` directly, so orchestration does not depend on generic shell templates.

## Non-goals

- Rich role/task prompt templating and artifact parsing from Codex output.
- Streaming logs via websocket.

## References

- Product spec: `docs/PRODUCT_SPEC.md#6-acceptance-criteria-mvp`
- Architecture: `docs/ARCHITECTURE.md#2-why-host-runner-exists`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Add `HOST_RUNNER_EXECUTOR=codex` path in host-runner.
- Execute local `codex exec` with configurable binary and args.
- Preserve workspace cwd behavior for shared-workspace tasks.
- Return stdout/stderr/exit_code in runner task metadata.
- Add host-runner tests for codex executor success and failure.
- Add API test that dispatch submit payload includes callback url/token fields when configured.

## Acceptance criteria

- [x] Runner supports `mock`, `shell`, and `codex` executors.
- [x] `codex` executor runs `codex exec` using env-driven config.
- [x] Success/failure metadata is reported in runner task result.
- [x] Tests cover codex executor and callback payload propagation.

## Implementation notes

Use `subprocess.run` with argument list (no shell expansion) for safer execution.

## Test plan

- [x] `apps/host-runner` tests for codex command execution.
- [x] `apps/api` tests for callback fields in runner submit payload.
- [x] Full regressions and UI build.

## Risks and mitigations

- Risk: local codex CLI flags may vary by version.
- Mitigation: keep command configurable via `HOST_RUNNER_CODEX_BIN` and `HOST_RUNNER_CODEX_ARGS`.

## Result

Implemented native `codex` executor in host-runner:

- Added execution branch `HOST_RUNNER_EXECUTOR=codex` in runner lifecycle.
- Added env-driven codex command configuration:
  - `HOST_RUNNER_CODEX_BIN` (default `codex`)
  - `HOST_RUNNER_CODEX_ARGS` (space-separated args, parsed safely)
- Runner now executes command:
  - `<HOST_RUNNER_CODEX_BIN> exec <HOST_RUNNER_CODEX_ARGS...> <prompt>`
- Preserved workspace cwd behavior (`shared-workspace` uses `workspace.project_root`).
- Added explicit error handling for missing codex binary and timeouts.
- Added tests:
  - host-runner codex success path with command/cwd assertions
  - host-runner missing binary failure path
  - API dispatch payload callback field propagation (`status_callback_url`, `status_callback_token`)

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `38 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `8 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/ui`: `npm run build` successful
