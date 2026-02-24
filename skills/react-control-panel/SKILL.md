---
name: react-control-panel
description: Build the React control panel for projects, roles, workflows, and run monitoring. Use when implementing UI flows for agent configuration, DAG editing, logs, approvals, and multi-project navigation.
---

# React Control Panel

## Overview

Design UI around operator workflows: configure, run, observe, intervene.
Favor clear state visibility over decorative complexity.

## Core screens

1. Projects list and project detail.
2. Agent roles CRUD.
3. Workflow builder (DAG editor).
4. Run timeline with task states and logs.
5. Approvals inbox.

## Engineering rules

- Keep API calls centralized.
- Use optimistic updates only when rollback is safe.
- Render run status transitions in near-real-time.
- Keep forms schema-driven for consistency.
- Use `$context7-doc-research` for framework-specific API uncertainty.

See `references/ui-ia.md` for information architecture.
