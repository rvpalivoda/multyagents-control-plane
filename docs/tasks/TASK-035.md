# Task 035: Enable artifact-based handoff in workflow DAG

## Metadata

- Status: `in_progress`
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

- [ ] Workflow step can declare required artifact types/labels from dependencies.
- [ ] Dispatcher blocks step until required artifacts are present.
- [ ] On success, task run shows resolved handoff artifact references.
- [ ] Integration scenario validates code -> review -> report handoff chain.

## Implementation notes

Keep default behavior unchanged for workflows without handoff filters to preserve backward compatibility.

Execution lane:
- Lane B in `docs/EXECUTION_BOARD.md` (parallel implementation track).

## Test plan

- [ ] Unit tests for readiness logic with and without artifact constraints.
- [ ] API tests for workflow schema updates and persisted handoff references.
- [ ] Integration test for multi-step artifact-driven DAG run.

## Risks and mitigations

- Risk: Deadlocks when artifact conditions are too strict.
- Mitigation: Add explicit operator diagnostics explaining unmet conditions.

## Result

Planned.
