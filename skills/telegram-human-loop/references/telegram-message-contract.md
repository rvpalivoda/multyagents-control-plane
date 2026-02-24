# Telegram Message Contract

## Approval request message

- Header: run and task identifiers
- Summary: why approval is required
- Actions: approve/reject links or commands

## Failure alert message

- Run ID
- Failed task ID
- Error summary
- Next suggested command (`/status`, `/resume`, `/abort`)

## Audit mapping

Each command must map to:
- operator id
- command
- target id
- timestamp
- result
