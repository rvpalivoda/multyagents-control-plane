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
   - Security adversarial regression pack (`apps/api/tests/test_api_security_adversarial.py`):
     - shared-workspace path traversal rejection (`..` escape attempts)
     - symlink escape rejection for lock paths and docker mounts
     - execution policy bypass rejection (`sandbox` not allowed outside `docker-sandbox`)
     - secret redaction checks for runner submit/status failure surfaces
   - Failure injection regression pack (`apps/api/tests/test_api_failure_injection_regression.py`):
     - runner unreachable/network-style submit failure
     - permission/policy denial triage path
     - retry + triage surface consistency (`task`, `task audit`, `events`, `workflow run`)

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

## Targeted deterministic security command

- `cd apps/api && .venv/bin/pytest -q tests/test_api_security_adversarial.py`
- Purpose: fast local regression checks for policy bypass attempts and secret-leak prevention.

## Bug policy
If a test fails:
1. create/attach task in `docs/tasks`
2. fix in same branch when possible
3. add regression test before closing task
