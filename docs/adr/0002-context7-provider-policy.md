# ADR-0002: Adopt Context7 with explicit role/task policy

## Status

Accepted

## Context

The platform needs up-to-date external library documentation for coding tasks.
Using Context7 globally for all tasks would introduce unnecessary latency and noise for non-coding workflows.

## Decision

Adopt Context7 as a configurable knowledge provider with explicit policy:
- role-level default: `context7_enabled` (boolean)
- task-level override: `context7_mode` (`inherit`, `force_on`, `force_off`)
- resolved effective value is forwarded to runner payload and stored in task audit

## Consequences

Benefits:
- deterministic behavior
- visibility and auditability of provider usage
- flexible control for code vs non-code workloads

Costs:
- additional schema fields in role/task models
- extra policy-resolution logic in API dispatch

## Alternatives considered

- Always-on Context7 for all tasks
- No Context7 integration and rely on web search/manual docs only
