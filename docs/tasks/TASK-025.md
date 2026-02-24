# Task 025: Extend Telegram commands with `next` and `cancel`

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Expose newly added orchestration controls in Telegram so operator can progress DAG runs and cancel tasks directly from chat.

## Non-goals

- Rich natural-language command parser.
- Full bidirectional push notifications to Telegram chats.

## References

- Product spec: `docs/PRODUCT_SPEC.md#7-telegram-integration`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-3-human-in-the-loop-2-3-days`

## Scope

- Add `/next <run_id>` -> `POST /workflow-runs/{run_id}/dispatch-ready`.
- Add `/cancel <task_id>` -> `POST /tasks/{task_id}/cancel`.
- Update command discovery endpoint output.
- Extend bot tests for route mapping and command list.

## Acceptance criteria

- [x] Telegram bot supports `next` and `cancel`.
- [x] Commands map to correct API routes.
- [x] Tests cover new command routing and discovery list.

## Implementation notes

Keep one-argument command shape for consistency with existing parser.

## Test plan

- [x] Extend `apps/telegram-bot` command route tests.
- [x] Full regressions and UI build.

## Risks and mitigations

- Risk: operators may confuse `/abort` and `/cancel`.
- Mitigation: keep explicit command docs and response messages.

## Result

Implemented Telegram command extensions for new run/task controls:

- Added command routes:
  - `/next <run_id>` -> `POST /workflow-runs/{run_id}/dispatch-ready`
  - `/cancel <task_id>` -> `POST /tasks/{task_id}/cancel`
- Updated unsupported command help message to include new commands.
- Updated command discovery endpoint output to include `next` and `cancel`.
- Added bot tests:
  - command list includes `cancel` and `next`
  - `/next` route mapping test
  - `/cancel` route mapping test
- Updated `apps/telegram-bot/README.md` command documentation.

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `41 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `8 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `12 passed`
- `apps/ui`: `npm run build` successful
