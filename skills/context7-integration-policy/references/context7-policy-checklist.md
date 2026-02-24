# Context7 Policy Checklist

## Schema

- Role schema contains `context7_enabled` boolean
- Task schema contains `context7_mode` enum
- Audit schema stores effective provider mode

## Resolution logic

- Deterministic precedence implemented
- Unit tests for all mode combinations
- Unknown values rejected by validation

## API/UI

- Role and task forms expose Context7 controls
- Run detail screen shows effective Context7 mode per task
- API responses include resolved context provider state

## Runner

- Submit payload carries resolved Context7 flags
- Runner logs provider mode at task start
