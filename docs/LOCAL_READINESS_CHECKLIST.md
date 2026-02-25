# Local Readiness Checklist (Go/No-Go)

Updated: 2026-02-25
Owner: Roman + ClawBot

## Legend
- 🟢 GO: ready for daily local use
- 🟡 PARTIAL: usable with known limitation
- 🔴 NO-GO: must fix before daily use

## 1) Core workflow capability
- 🟢 Partial rerun of failed branches (`TASK-057`) — implemented
- 🟡 Process transparency timeline (`TASK-058`) — phase 1 done; phase 2 pending (full timeline rows)
- 🟢 Handoff board + dispatch gating (`TASK-048`) — implemented
- 🟢 Retry + triage baseline (`TASK-049`, `TASK-052`) — implemented

## 2) Local runtime and operations
- 🟢 Local bootstrap docs/runbook (`TASK-060`, `TASK-062`) — implemented
- 🟢 E2E readiness scenarios docs/scripts (`TASK-061`) — integrated
- 🟢 Compose + env docs present (`infra/compose/*`) — present
- 🟡 One-command local smoke verified on this host — partial (depends on local env and service state)

## 3) Quality and regressions
- 🟢 API tests passing in local env (`apps/api`)
- 🟡 UI vitest exit stability in this environment — intermittent hang after run output (tests themselves pass)
- 🟢 UI production build passes (`vite build`)
- 🟡 Contract regression suite (`TASK-063`) — pending dedicated suite completion

## 4) Product packs and usability
- 🟢 Content workflow presets (`TASK-055`) — implemented
- 🟡 Developer workflow pack (`TASK-059`) — pending
- 🟡 Template recommender (`TASK-053`) — pending

---

## Current decision

**Overall: 🟡 PARTIAL GO**

You can start daily local usage now for real runs, with two caveats:
1. transparency timeline is not fully finished (TASK-058 phase 2),
2. UI test runner process occasionally hangs post-run in this environment.

---

## Must-do before full GO
1. Finish `TASK-058` phase 2 (full timeline branch/owner/stage/blockers)
2. Close `TASK-064` with evidence links and stable smoke run
3. Complete `TASK-063` contract regression suite
4. Complete `TASK-059` dev workflow pack

---

## Evidence pointers
- Backlog: `docs/BACKLOG.md`
- Tasks: `docs/tasks/TASK-057.md`, `TASK-058.md`, `TASK-060.md`, `TASK-061.md`, `TASK-062.md`, `TASK-063.md`, `TASK-064.md`
- Compose docs: `infra/compose/README.md`
- Ops runbook: `docs/LOCAL_GATEWAY_SANDBOX_FIX.md`


## Quick validation commands

- `./scripts/multyagents readiness`
- `./scripts/ui-test-smoke.sh`
- `cd apps/ui && npm run build`
- `cd apps/api && .venv/bin/pytest -q`
