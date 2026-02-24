# Task 010: Telegram bot command set (`run/status/approve/pause/resume/abort`)

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Implement Telegram-facing command handling for operator control actions:
`run`, `status`, `approve`, `pause`, `resume`, `abort`.

## Non-goals

- Full Telegram Bot API integration (sending messages to real chats).
- Full workflow/approval backend implementation in API.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-3-human-in-the-loop-2-3-days`

## Scope

- Add command parser and dispatcher in `telegram-bot`.
- Add webhook endpoint to parse Telegram update payload.
- Map commands to API calls with explicit routes and result status.
- Add tests for supported commands and error cases.

## Acceptance criteria

- [x] Bot supports `run/status/approve/pause/resume/abort` commands.
- [x] Invalid/unknown command inputs return explicit response.
- [x] Webhook parser handles text commands from Telegram update payload.
- [x] Tests cover command mapping and webhook behavior.

## Implementation notes

Use synchronous API call adapter (`httpx.request`) with graceful handling for API errors/unavailable endpoints.
Return structured command response for both local command endpoint and webhook endpoint.

## Test plan

- [x] Bot unit/API tests for command parser + dispatcher.
- [x] Bot tests for webhook payload handling.

## Risks and mitigations

- Risk: API endpoints for run control may not exist yet and return 404.
- Mitigation: treat non-2xx as handled command with explicit failed status and code.

## Result

Implemented:
- Added command registry for `run/status/approve/pause/resume/abort`.
- Added structured command response model with `handled/ok/api_status` fields.
- Added local command endpoint: `POST /telegram/command`.
- Added Telegram update handler endpoint: `POST /telegram/webhook`.
- Added command discovery endpoint: `GET /telegram/commands`.
- Added API adapter with graceful behavior for non-2xx and network failures.
- Added comprehensive tests for command routing, validation, unknown commands, and webhook parsing.

Verification:
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `9 passed`
- `apps/api`: `./.venv/bin/pytest -q` -> `26 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `4 passed`
- `apps/ui`: `npm run build` succeeded
