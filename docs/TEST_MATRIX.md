# Test Matrix

| Area | Command | Expected |
|---|---|---|
| API full regression | `cd apps/api && .venv/bin/pytest -q` | all passed |
| Bot regression | `cd apps/telegram-bot && .venv/bin/pytest -q` | all passed |
| UI build | `cd apps/ui && npm run build` | success |
| UI smoke | `./scripts/ui-test-smoke.sh` | all passed |
| Security adversarial regression (TASK-074) | `cd apps/api && .venv/bin/pytest -q tests/test_api_security_adversarial.py` | all passed |
| Compose E2E | `./scripts/multyagents e2e` | smoke passed |
| Parallel stress smoke | `STRESS_RUNS=20 STRESS_PARALLELISM=6 ./scripts/multyagents stress-smoke` | summary `failed=0` |
| Concurrency race stress (TASK-072) | `./scripts/multyagents race-stress` | summary `overall_status=pass`, invariants `passed=total` |
| Restart persistence invariants (TASK-073) | `./scripts/multyagents restart-persistence` | summary `overall_status=pass`, invariants `passed=total` |
| Chaos failure drills (TASK-071) | `./scripts/multyagents chaos` | summary `overall_status=success` (allows `expected_pending`) |
| Local readiness | `./scripts/multyagents readiness` | scenarios run + evidence generated |
| Release gate v2 hard-fail (TASK-077) | `./scripts/multyagents gate-v2` | final verdict `PASS`, all stages `PASS`, evidence `docs/evidence/task-077/latest.json` |

## Real-case checks

1. Create project in arbitrary absolute folder under `/tmp`.
2. Create role + workflow for that project.
3. Create run + dispatch + success.
4. Trigger failure and verify triage fields.
5. Trigger partial rerun and verify behavior (`success` or explicit `expected_pending` with reason).
