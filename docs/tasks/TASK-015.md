# Task 015: Integrate Context7 as configurable knowledge provider

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Add first-class support for Context7 in the platform so operators can enable or disable it per role and per task, with clear policy and audit behavior.

## Non-goals

- Replace all documentation sources with Context7-only logic.
- Implement external vendor abstraction beyond Context7 in this task.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#7-security-model`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Add role-level flag `context7_enabled` and policy defaults.
- Add task-level override `context7_mode` (`inherit`, `force_on`, `force_off`).
- Extend runner submit payload with resolved Context7 settings.
- Add UI controls for role and task Context7 configuration.
- Persist Context7 usage metadata in run/task audit.

## Acceptance criteria

- [x] Role and task schemas support Context7 settings.
- [x] Runner receives effective Context7 configuration per task.
- [x] UI can configure and display Context7 policy values.
- [x] Run/task audit shows whether Context7 was enabled.
- [x] Integration test covers one flow with Context7 enabled and one disabled.

## Implementation notes

Keep settings explicit and deterministic:
- role default policy
- task override
- final resolved value in execution payload

Do not infer policy from task type automatically in backend without explicit defaults.

## Test plan

- [x] Unit tests for settings resolution logic.
- [x] API tests for role/task config persistence.
- [x] Integration test verifying runner payload and audit records.
- [ ] Manual test in UI for role/task edit forms.

## Risks and mitigations

- Risk: overusing Context7 in non-coding tasks can add latency and noise.
- Mitigation: default to `inherit` and allow explicit `force_off` per task.

## Result

Started implementation via skills and process preparation:
- Added `skills/context7-integration-policy`
- Added `skills/context7-doc-research`
- Added Context7 integration task in backlog

Implemented API-side Context7 policy behavior:
- Added Python API project scaffold under `apps/api`
- Added role field `context7_enabled`
- Added task field `context7_mode` (`inherit`, `force_on`, `force_off`)
- Added deterministic resolver and dispatch payload generation
- Added task audit endpoint with resolved Context7 state
- Added React UI scaffold under `apps/ui` with role/task Context7 controls and dispatch+audit view

Verification:
- Ran `pytest` in `apps/api`
- Result: `6 passed`
- Ran `npm run build` in `apps/ui`
- Result: production build succeeded
