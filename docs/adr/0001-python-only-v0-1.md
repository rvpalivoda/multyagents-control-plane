# ADR-0001: Python-only backend baseline for v0.1

## Status

Accepted

## Context

Project is a local personal tool. Primary objective is fast iteration with minimal operational overhead.
Using multiple backend languages at MVP stage increases complexity in tooling, debugging, and maintenance.

## Decision

Use Python-only backend baseline for v0.1:
- `apps/api`: Python (FastAPI)
- `apps/telegram-bot`: Python
- `apps/host-runner`: Python process on host invoking local `codex` CLI

Frontend remains React + TypeScript.

## Consequences

Benefits:
- faster MVP delivery
- single-language backend stack
- easier local maintenance for one operator

Costs:
- potential performance limits for very high concurrency workloads

Risk handling:
- keep runner protocol language-neutral so runner can be reimplemented later (e.g. Go) without API redesign.

## Alternatives considered

- Mixed stack (Python API + Go runner)
- Full Go backend
