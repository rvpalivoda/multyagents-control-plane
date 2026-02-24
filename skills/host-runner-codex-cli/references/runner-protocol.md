# Runner Protocol (Minimal)

## Submit request

- `task_id`
- `run_id`
- `role_name`
- `execution_mode`
- `workspace_path` (optional)
- `prompt`
- `timeout_seconds`

## Status callback

- `task_id`
- `status` (`running|waiting_approval|success|failed|canceled`)
- `message`
- `timestamp`

## Log event

- `task_id`
- `stream` (`stdout|stderr|system`)
- `chunk`
- `offset`
