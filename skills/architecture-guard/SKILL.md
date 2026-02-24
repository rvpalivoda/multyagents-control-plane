---
name: architecture-guard
description: Protect architectural consistency against scope drift and accidental coupling. Use when implementing features that may change boundaries, service contracts, data models, deployment topology, or reliability constraints.
---

# Architecture Guard

## Overview

Apply architecture checks before and after implementation to keep the platform coherent.
Escalate structural changes into explicit ADR decisions.

## Workflow

1. Identify touched components and boundaries.
2. Check consistency with `docs/ARCHITECTURE.md`.
3. Classify change as compatible, additive, or breaking.
4. If breaking or cross-cutting, add/update ADR.
5. Update impacted architecture sections and implementation plan.

## Decision rules

- Keep runner transport and contracts language-neutral.
- Avoid direct coupling between UI and runner.
- Keep event/artifact schemas versioned.
- Require migration notes for data model changes.

For impact classification, read `references/impact-matrix.md`.
