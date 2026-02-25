# Test Matrix

| Area | Command | Expected |
|---|---|---|
| API full regression | `cd apps/api && .venv/bin/pytest -q` | all passed |
| Bot regression | `cd apps/telegram-bot && .venv/bin/pytest -q` | all passed |
| UI build | `cd apps/ui && npm run build` | success |
| UI smoke | `./scripts/ui-test-smoke.sh` | all passed |
| Compose E2E | `./scripts/multyagents e2e` | smoke passed |
| Parallel stress smoke | `STRESS_RUNS=20 STRESS_PARALLELISM=6 ./scripts/multyagents stress-smoke` | summary `failed=0` |
| Local readiness | `./scripts/multyagents readiness` | scenarios run + evidence generated |

## Real-case checks

1. Create project in arbitrary absolute folder under `/tmp`.
2. Create role + workflow for that project.
3. Create run + dispatch + success.
4. Trigger failure and verify triage fields.
5. Trigger partial rerun and verify behavior (`success` or explicit `expected_pending` with reason).
