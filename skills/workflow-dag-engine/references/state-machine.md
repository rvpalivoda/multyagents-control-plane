# Workflow State Machine

## Task states

- `queued`
- `running`
- `waiting_approval`
- `success`
- `failed`
- `canceled`

## Run states

- `created`
- `running`
- `blocked`
- `completed`
- `failed`
- `canceled`

## Transition rules

- `queued -> running` when worker acquired
- `running -> waiting_approval` when approval policy triggers
- `waiting_approval -> running` when approved
- `running -> success|failed` on terminal execution result
