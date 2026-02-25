# Test Strategy

Updated: 2026-02-25

## Goal
Provide high confidence for daily production-like local usage across orchestration, UI, runner integration, and operator workflows.

## Layers

1. **Unit tests**
   - Store/business logic
   - Validation and scoring helpers

2. **API integration tests**
   - FastAPI endpoints via `TestClient`
   - Contract stability (additive fields only)
   - Negative paths and policy enforcement

3. **UI critical-path tests**
   - Workflow builder
   - Runs center controls
   - Recommendation + quick launch interactions

4. **System E2E smoke**
   - `./scripts/multyagents e2e`
   - Compose stack + host-runner mock execution

5. **Operational readiness tests**
   - `./scripts/multyagents readiness`
   - Evidence artifact generation
   - Recovery flow scripts

## Release gate
A release candidate is valid only when all are green:
- `apps/api`: full pytest
- `apps/telegram-bot`: pytest
- `apps/ui`: build + smoke vitest
- compose e2e smoke
- readiness scenario run

## Bug policy
If a test fails:
1. create/attach task in `docs/tasks`
2. fix in same branch when possible
3. add regression test before closing task
