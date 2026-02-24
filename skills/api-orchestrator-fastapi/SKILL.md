---
name: api-orchestrator-fastapi
description: Implement and evolve the Python FastAPI orchestration backend. Use when building API endpoints, workflow scheduling services, persistence logic, policy enforcement, and runner integration contracts.
---

# API Orchestrator FastAPI

## Overview

Build orchestration features with clear separation: transport layer, domain services, and persistence.
Keep DTOs explicit and compatible.

## Workflow

1. Define/extend request-response schema.
2. Implement domain service behavior.
3. Add repository/migration changes if needed.
4. Expose endpoint with validation and error mapping.
5. Add tests for service and API behavior.

## Engineering rules

- Keep endpoint handlers thin.
- Enforce policy checks before task execution.
- Persist state transitions atomically.
- Return stable error codes for automation.
- For external dependency behavior, pair with `$context7-doc-research`.

Use `references/api-layout.md` for module boundaries and checklist.
