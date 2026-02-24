# Task 007: Implement host runner protocol integration (submit/cancel/status)

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Connect orchestrator dispatch flow to host-runner protocol so task dispatch can submit to runner endpoint and report submission result.

## Non-goals

- Full process execution and streaming logs from real codex runs.
- Production-grade retry queue for runner calls.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Add API runner client for submit calls.
- Extend dispatch response with runner submission status.
- Preserve graceful behavior when runner is unavailable.
- Keep host-runner API compatible with submit/status/cancel scaffold.

## Acceptance criteria

- [x] Dispatch attempts runner submission when runner URL is configured.
- [x] Dispatch remains successful with explicit fallback status when runner is not configured/reachable.
- [x] API tests cover runner submission status behavior.

## Implementation notes

Use best-effort submit at dispatch stage to avoid blocking orchestration progress on runner transport issues.

## Test plan

- [x] API tests for dispatch with runner disabled.
- [x] API tests for dispatch with mocked successful runner submit.

## Risks and mitigations

- Risk: flaky runner network causing dispatch failure.
- Mitigation: non-fatal runner submit errors with explicit status in response.

## Result

Implemented:
- Added API runner client (`apps/api/src/multyagents_api/runner_client.py`) with best-effort submit behavior.
- Dispatch flow now includes `runner_submission` in response.
- Added runtime dependency `httpx` for API runner calls.
- Kept graceful fallback when runner URL is not configured or submit fails.

Verification:
- `apps/api`: `pytest` -> `18 passed`

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
