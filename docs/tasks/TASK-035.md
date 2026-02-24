# Task 035: Enable artifact-based handoff in workflow DAG

## Metadata

- Status: `review`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-24`

## Objective

Allow downstream steps to consume explicit artifacts/events from upstream steps as part of DAG readiness and handoff.

## Non-goals

- Full workflow language redesign.
- Automatic semantic merge of conflicting artifacts.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-2-execution-pipeline-4-5-days`

## Scope

- Extend workflow step definition with optional artifact requirements/labels.
- Update dispatcher to gate readiness by dependency + artifact conditions.
- Persist handoff references in task run records.
- Surface handoff chain in timeline/task UI payloads.

## Acceptance criteria

- [x] Workflow step can declare required artifact types/labels from dependencies.
- [x] Dispatcher blocks step until required artifacts are present.
- [x] On success, task run shows resolved handoff artifact references.
- [x] Integration scenario validates code -> review -> report handoff chain.

## Implementation notes

Keep default behavior unchanged for workflows without handoff filters to preserve backward compatibility.

Execution lane:
- Lane B in `docs/EXECUTION_BOARD.md` (parallel implementation track).

## Test plan

- [x] Unit tests for readiness logic with and without artifact constraints.
- [x] API tests for workflow schema updates and persisted handoff references.
- [x] Integration test for multi-step artifact-driven DAG run.

## Risks and mitigations

- Risk: Deadlocks when artifact conditions are too strict.
- Mitigation: Add explicit operator diagnostics explaining unmet conditions.

## Result

Implemented artifact-based DAG handoff and readiness gating:

- Extended workflow step schema with `required_artifacts` (source dependency, artifact type, label).
- Added dispatcher readiness checks for artifact constraints in workflow runs.
- Added consumed handoff artifact references to task audit (`consumed_artifact_ids`).
- Included consumed artifact references in `task.dispatched` event payload for timeline visibility.

Execution evidence:

- `apps/api`: `pytest -q` -> `60 passed`.

Commits:
- `be0af21` (`feat(task-035): gate workflow dispatch by artifact handoff`)
