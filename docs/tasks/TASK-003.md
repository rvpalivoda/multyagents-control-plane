# Task 003: Add shared API contracts and schema versioning

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Create a shared, versioned API contract package so backend and frontend use one source for core Context7 data models.

## Non-goals

- Full code generation pipeline for all languages.
- Replacing all API models with generated classes in one step.

## References

- Product spec: `docs/PRODUCT_SPEC.md#4-non-functional-requirements`
- Architecture: `docs/ARCHITECTURE.md#6-inter-agent-contract`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Add `packages/contracts` with versioned schema files.
- Define schema for role/task/dispatch/audit Context7 models.
- Expose contract version from API.
- Consume shared TypeScript contract types in UI.

## Acceptance criteria

- [x] Versioned schema files exist under `packages/contracts`.
- [x] API exposes contract version endpoint.
- [x] UI imports contract types from shared package (no duplicated local types for covered models).
- [x] Contract docs describe compatibility/update policy.

## Implementation notes

Start with Context7-focused models already implemented in API/UI, then extend package in future tasks.

## Test plan

- [x] API tests for contract version endpoint.
- [x] UI build succeeds with shared type imports.
- [x] Manual check of schema files and documentation.

## Risks and mitigations

- Risk: contract drift if schemas are not enforced.
- Mitigation: add clear versioning policy and keep contract changes explicit in task flow.

## Result

Implemented:
- Added shared contracts package:
  - `packages/contracts/v1/context7.schema.json`
  - `packages/contracts/ts/context7.ts`
  - `packages/contracts/README.md`
- Added API endpoint:
  - `GET /contracts/current`
- Switched UI context model types to shared contract imports.

Verification:
- `apps/api`: `pytest` -> `7 passed`
- `apps/ui`: `npm run build` succeeded
