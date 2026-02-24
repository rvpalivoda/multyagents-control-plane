---
name: telegram-human-loop
description: Implement Telegram human-in-the-loop controls for workflow runs. Use when building bot commands, approval handling, operational alerts, and secure operator interactions.
---

# Telegram Human Loop

## Overview

Use Telegram as a lightweight control channel for approvals and incident handling.
Keep command behavior deterministic and auditable.

## Commands

- `/run <workflow>`
- `/status <run_id>`
- `/pause <run_id>`
- `/resume <run_id>`
- `/approve <approval_id>`
- `/abort <run_id>`

## Rules

- Authenticate allowed operator chat IDs.
- Include run/task IDs in every actionable message.
- Require explicit confirmation for destructive actions.
- Mirror decisions back to API audit log.

Read `references/telegram-message-contract.md` for payload structure.
