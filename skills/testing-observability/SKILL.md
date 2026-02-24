---
name: testing-observability
description: Build confidence and visibility for the multi-agent platform. Use when adding unit/integration/smoke tests, structured logging, run metrics, audit trails, and failure diagnostics.
---

# Testing Observability

## Overview

Validate behavior at the level where failures are likely: state transitions, runner protocol, and approval gates.
Make failures diagnosable without reproducing full runs.

## Test workflow

1. Add unit tests for pure domain logic.
2. Add integration tests for API + DB + queue behavior.
3. Add smoke tests for host-runner protocol.
4. Verify telemetry for normal and failure paths.

## Observability rules

- Use structured logs with correlation IDs.
- Emit lifecycle events for every task transition.
- Track queue depth and run duration metrics.
- Keep audit timeline queryable per run.

See `references/test-matrix.md` for minimum coverage expectations.
