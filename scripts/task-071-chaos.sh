#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/infra/compose"
E2E_SCENARIO_SCRIPT=chaos_e2e_failure_drills.py ./scripts/run-e2e.sh
