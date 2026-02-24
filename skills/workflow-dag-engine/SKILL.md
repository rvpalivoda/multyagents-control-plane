---
name: workflow-dag-engine
description: Design and implement DAG-based workflow scheduling for multi-agent runs. Use when defining task dependencies, scheduling rules, retries, timeouts, approvals, and run state transitions.
---

# Workflow DAG Engine

## Overview

Treat workflow execution as a deterministic state machine over task nodes.
Keep dependency handling explicit and observable.

## Workflow

1. Validate DAG has no cycles.
2. Mark root-ready tasks.
3. Dispatch only tasks with satisfied dependencies.
4. Apply retries/timeouts per task policy.
5. Block on approval gates when required.
6. Finalize run from terminal task states.

## Invariants

- A task is executed at most once per attempt number.
- Failed dependency blocks downstream tasks.
- Manual approval changes state through explicit event.
- Run status derives from task terminal states.

See `references/state-machine.md` for transition table.
