# Task 016: Bootstrap monorepo structure for core services

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Create a stable project structure for all core services so implementation can proceed in parallel with clear boundaries.

## Non-goals

- Implement full business logic of each service.
- Add production deployment manifests.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Ensure app folders exist for `api`, `ui`, `telegram-bot`, `host-runner`.
- Add minimal runnable scaffold for missing services.
- Add repository-level structure for compose/infrastructure files.

## Acceptance criteria

- [x] `apps/telegram-bot` scaffold exists and is runnable.
- [x] `apps/host-runner` scaffold exists and is runnable.
- [x] `infra/compose` exists and includes base stack files.
- [x] Structure is documented for contributors.

## Implementation notes

Keep scaffolds intentionally minimal but executable to reduce bootstrap friction.

## Test plan

- [x] Run minimal health command/script for each new service.
- [x] Validate directory layout against backlog objective.

## Risks and mitigations

- Risk: over-engineered scaffolds create churn.
- Mitigation: add only minimal baseline and defer feature logic.

## Result

Implemented:
- Added `apps/telegram-bot` Python FastAPI scaffold with `/health` and `/config`.
- Added `apps/host-runner` Python FastAPI scaffold with `submit/get/cancel` endpoints.
- Added tests for both services.
- Added `infra/compose` directory with compose files and docs.
- Added root-level project `README.md` with structure and run commands.

Verification:
- `apps/telegram-bot`: `pytest` -> `2 passed`
- `apps/host-runner`: `pytest` -> `2 passed`
- Layout validated with repository tree inspection.
