---
name: events-artifacts-contract
description: Define and enforce event and artifact schemas for inter-agent collaboration. Use when designing message payloads, schema versions, compatibility rules, and storage contracts.
---

# Events Artifacts Contract

## Overview

Use machine-readable contracts for all agent communication.
Keep producers and consumers decoupled with versioned schemas.

## Workflow

1. Define event/artifact type and intent.
2. Specify required fields and validation rules.
3. Assign schema version.
4. Publish compatibility notes.
5. Add producer/consumer tests.

## Rules

- Never emit unversioned payloads.
- Keep IDs and timestamps mandatory.
- Avoid embedding large blobs inside events; link artifacts instead.
- Preserve backward compatibility for minor versions.

Read `references/schema-rules.md` for naming and versioning policy.
