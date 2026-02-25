# Security Policy

## Reporting a vulnerability

Please report vulnerabilities privately to the repository owner (@rvpalivoda).
Do not open public issues for active vulnerabilities.

## Scope

In scope:
- API auth/authorization gaps
- Sandbox/workspace escape risks
- Secret leakage in logs/events/artifacts
- Command injection / unsafe execution paths

## Hardening baseline

- Approval gates for risky operations
- Path policy enforcement in execution modes
- Isolation checks for worktree/sandbox modes
- Audit trail for task lifecycle actions
