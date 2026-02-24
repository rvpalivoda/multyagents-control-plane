# Schema Rules

## Naming

- Event type: `<domain>.<entity>.<action>`
- Artifact type: short stable nouns (`text`, `file`, `diff`, `commit`, `report`)

## Versioning

- Major: breaking field changes
- Minor: additive fields
- Patch: documentation-only or semantics clarification

## Required metadata

- `schema_version`
- `run_id`
- `task_id`
- `created_at`
