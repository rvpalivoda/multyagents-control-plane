# API Layout and Checklist

## Suggested layout

- `apps/api/src/api/` routers and DTO binding
- `apps/api/src/services/` orchestration logic
- `apps/api/src/repos/` database access
- `apps/api/src/models/` SQLAlchemy models
- `apps/api/src/policies/` permission/approval checks

## Endpoint checklist

- Input schema validated
- Domain errors mapped to HTTP codes
- State transition event emitted
- Audit row persisted
- Tests added (happy path + failure path)
