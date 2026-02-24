---
name: docker-local-stack
description: Manage Docker-based local control plane services for the multi-agent platform. Use when creating or updating compose files, service wiring, environment configuration, and local startup/health workflows.
---

# Docker Local Stack

## Overview

Run UI/API/DB/Redis/Bot as a reproducible local stack.
Keep host-runner outside containers and connected through explicit endpoint config.

## Workflow

1. Define core services and networks.
2. Configure env vars and secrets strategy.
3. Add healthchecks and startup dependencies.
4. Validate local boot and shutdown behavior.
5. Document operational commands.

## Rules

- Do not run local Codex CLI inside containers.
- Keep data services persistent via named volumes.
- Pin major versions for base images.

See `references/compose-checklist.md` for validation points.
