---
name: project-workspace-git
description: Manage project file access and git modes for agent execution. Use when implementing shared workspace locks, isolated worktrees, branch naming, and merge safety checks.
---

# Project Workspace Git

## Overview

Support both collaborative and isolated execution modes without corrupting project state.
Make file ownership and merge behavior explicit.

## Modes

- `no-workspace`: no repository access
- `shared-workspace`: shared path with soft lock policy
- `isolated-worktree`: per-task branch and worktree

## Workflow

1. Resolve project root and allowed paths.
2. Apply mode-specific preparation.
3. Enforce lock or branch policy.
4. Execute task.
5. Collect changes and cleanup temporary resources.

## Safety rules

- Never bypass path policy.
- Never auto-merge without reviewer gate.
- Cleanup stale worktrees and lock leases.

Use `references/git-ops-checklist.md` for operational checks.
