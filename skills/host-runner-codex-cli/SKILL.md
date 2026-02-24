---
name: host-runner-codex-cli
description: Build and maintain the Python host runner that invokes local Codex CLI for agent tasks. Use when implementing process execution, cancellation, streaming logs, and runner-to-API status reporting.
---

# Host Runner Codex CLI

## Overview

Run Codex locally from host while keeping control plane in Docker.
Provide reliable submit, cancel, and status semantics.

## Workflow

1. Receive task payload from API.
2. Materialize execution context (workspace, env, limits).
3. Spawn `codex` process with structured I/O capture.
4. Stream logs/events to API.
5. Handle cancel/timeout signals.
6. Publish terminal result and artifacts.

## Reliability rules

- Track pid and correlation IDs per task.
- Flush stdout/stderr incrementally.
- Guarantee final status callback once.
- Reconcile orphaned tasks after restart.
- Use `$context7-integration-policy` for provider mode resolution behavior.

See `references/runner-protocol.md` for message contracts.
