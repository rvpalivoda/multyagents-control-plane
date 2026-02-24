# Task 034: Add event and artifact contract plus persistence APIs

## Metadata

- Status: `review`
- Priority: `P0`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-24`

## Objective

Create explicit, versioned inter-agent event/artifact contracts and API endpoints for durable storage/query.

## Non-goals

- Binary artifact blob storage backend.
- Cross-project global analytics.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#6-inter-agent-contract`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Define schemas for events and artifacts (`event_type`, producer, payload, artifact_type, location, summary).
- Add persistence entities and API endpoints for create/list/filter.
- Link events/artifacts to runs/tasks and include them in task audit views.
- Add contract versioning markers to avoid breaking changes.

## Acceptance criteria

- [x] API validates event/artifact payloads against defined schema.
- [x] Events/artifacts are persisted and queryable by `run_id`, `task_id`, and type.
- [x] Task audit includes produced artifacts and key event records.
- [x] Tests cover schema validation and filtered retrieval behavior.

## Implementation notes

Use additive schema evolution and keep compatibility with existing `/events` timeline consumers.

## Test plan

- [x] API unit tests for schema validation and persistence behavior.
- [x] Integration-like API test that emits events/artifacts during run progression.
- [ ] Contract snapshot test for schema version stability.

## Risks and mitigations

- Risk: Payload shape drift across producers.
- Mitigation: Centralize schema package and reject non-conformant writes.

## Result

Implemented:

- Extended contracts with version marker `contract_version=v1` and schema validation:
  - `EventCreate` / `EventRead`
  - `ArtifactCreate` / `ArtifactRead`
- Added artifact domain model and persistence in API store with filtered query by `run_id`, `task_id`, `artifact_type`.
- Added event ingestion endpoint and filtering by `event_type`.
- Linked event/artifact records into task audit:
  - `recent_event_ids`
  - `produced_artifact_ids`
- Preserved snapshot persistence compatibility and added artifact persistence.

API endpoints added/extended:

- `POST /events`
- `GET /events` (`run_id`, `task_id`, `event_type`, `limit`)
- `POST /artifacts`
- `GET /artifacts` (`run_id`, `task_id`, `artifact_type`, `limit`)

Verification:

- `cd apps/api && .venv/bin/pytest -q` -> `56 passed`
