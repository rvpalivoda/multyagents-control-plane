---
name: context7-integration-policy
description: Integrate and operate Context7 as a configurable knowledge provider in the multi-agent platform. Use when defining role/task configuration, effective policy resolution, runner payload fields, audit requirements, and fallback behavior for documentation retrieval.
---

# Context7 Integration Policy

## Overview

Treat Context7 as a controlled capability, not a hidden global default.
Resolve behavior from explicit policy fields and persist the final decision in task audit data.

## Workflow

1. Add role-level default setting for Context7 usage.
2. Add task-level override with deterministic precedence.
3. Compute effective setting before dispatch to runner.
4. Include effective setting in runner payload.
5. Persist effective setting in task execution metadata.
6. Expose this state in UI and run timeline.

## Policy model

- `role.context7_enabled`: boolean default.
- `task.context7_mode`: `inherit | force_on | force_off`.
- Effective resolution:
  - `force_on` => enabled
  - `force_off` => disabled
  - `inherit` => use role default

## Failure behavior

- If Context7 is enabled but unavailable, log provider error and continue task execution only if role policy allows fallback.
- If fallback is disallowed, fail task with explicit provider error status.

Use `references/context7-policy-checklist.md` for implementation and review checks.
