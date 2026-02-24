# Task 028: Add task listing API and UI task explorer

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Improve operator control by exposing task list views and selection from UI, including filtering by workflow run.

## Non-goals

- Full pagination and sorting controls.
- Full-text search over task history.

## References

- Product spec: `docs/PRODUCT_SPEC.md#2-primary-users`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-1-core-domain-3-4-days`

## Scope

- Add API endpoint:
  - `GET /tasks` with optional `run_id`.
- Add store list method with optional run filter.
- Add UI “Task Explorer” table:
  - list tasks
  - optional filter by selected run
  - click row to select active task
  - refresh action
- Add API tests for list endpoint and run filtering.

## Acceptance criteria

- [x] API returns task list and supports filtering by run id.
- [x] UI shows task table and allows selecting a task.
- [x] Tests cover list and filtered list behavior.

## Implementation notes

Reuse existing task detail payload (`TaskRead`) for consistency.

## Test plan

- [x] API tests for `/tasks` list/filter.
- [x] Full regressions and UI build.

## Risks and mitigations

- Risk: task list growth can impact UX/performance.
- Mitigation: keep endpoint shape simple and prepare for pagination in next iteration.

## Result

Implemented task listing and task explorer controls:

- API:
  - Added `GET /tasks` endpoint with optional `run_id` filter.
  - Added store list method with run existence validation and filtered results.
- UI:
  - Added `Task Explorer` section with:
    - run id filter input
    - refresh and clear filter actions
    - task table (id/title/status/mode/role/project)
    - row click to select active task and load timeline for selected task.
  - Integrated task list refresh after create/dispatch/cancel/refresh actions.
- Added API tests:
  - `apps/api/tests/test_api_tasks_list.py`
    - list returns created tasks
    - run-filtered list works
    - missing run filter returns `404`

Verification:

- `apps/api`: `./.venv/bin/pytest -q` -> `47 passed`
- `apps/host-runner`: `./.venv/bin/pytest -q` -> `10 passed`
- `apps/telegram-bot`: `./.venv/bin/pytest -q` -> `12 passed`
- `apps/ui`: `npm run build` successful

Commits:
- `28be9f3` (`feat(task-016): bootstrap monorepo baseline`)
