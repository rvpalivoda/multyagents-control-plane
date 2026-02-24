# Task 002: Add base docker-compose for core services

## Metadata

- Status: `done`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Provide a working local Docker stack for control plane services with clear env wiring and health checks.

## Non-goals

- Production-grade scaling and HA settings.
- Containerizing host-runner or local codex binary.

## References

- Product spec: `docs/PRODUCT_SPEC.md#6-acceptance-criteria-mvp`
- Architecture: `docs/ARCHITECTURE.md#9-deployment-topology`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Add compose file for `ui`, `api`, `postgres`, `redis`, `telegram-bot`.
- Add baseline Dockerfiles and env examples for containerized services.
- Keep host-runner outside compose, configured via env endpoint.

## Acceptance criteria

- [x] `docker compose config` succeeds.
- [x] Core services are defined with persistent volumes for DB/cache.
- [x] API and UI ports are exposed for local development.
- [x] Host-runner endpoint is configurable via env.

## Implementation notes

Use simple compose profile with predictable local ports and health checks.

## Test plan

- [x] Run `docker compose config` on compose file.
- [x] If docker daemon is available, run stack and verify service health.

## Risks and mitigations

- Risk: local environment differences break startup.
- Mitigation: provide defaults and explicit env variables.

## Result

Implemented:
- Added `infra/compose/docker-compose.yml` with services:
  - `postgres`, `redis`, `api`, `ui`, `telegram-bot`
- Added baseline Dockerfiles:
  - `apps/api/Dockerfile`
  - `apps/ui/Dockerfile`
  - `apps/telegram-bot/Dockerfile`
- Added env template: `infra/compose/.env.example`
- Added usage doc: `infra/compose/README.md`

Verification:
- Ran `docker compose config` successfully from `infra/compose`.
- Ran `docker compose up --build -d` for full stack smoke test.
- Verified health endpoints:
  - `api /health` -> 200
  - `telegram-bot /health` -> 200
  - `ui /` -> 200
- Stack shutdown completed with `docker compose down --remove-orphans`.

Notes:
- Default host ports were busy in this environment, so compose now supports env-configurable ports (`*_PORT`), including dynamic host port binding with `0`.
