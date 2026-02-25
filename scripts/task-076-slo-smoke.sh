#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
EVIDENCE_DIR="${TASK_076_EVIDENCE_DIR:-$ROOT_DIR/docs/evidence/task-076}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -n "${API_PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$API_PYTHON_BIN"
elif [[ -x "$API_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$API_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

mkdir -p "$EVIDENCE_DIR"

JSON_EVIDENCE="$EVIDENCE_DIR/task-076-slo-performance-$TIMESTAMP.json"
MD_EVIDENCE="$EVIDENCE_DIR/task-076-slo-performance-$TIMESTAMP.md"
PYTEST_LOG="$EVIDENCE_DIR/task-076-pytest-$TIMESTAMP.log"

echo "[task-076] using python: $PYTHON_BIN"

echo "[task-076] running SLO load/soak benchmark suite"
PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" "$API_DIR/scripts/task_076_slo_performance.py" \
  --output-json "$JSON_EVIDENCE" \
  --output-md "$MD_EVIDENCE" \
  --load-runs "${TASK_076_LOAD_RUNS:-16}" \
  --soak-runs "${TASK_076_SOAK_RUNS:-60}" \
  --steps-per-run "${TASK_076_STEPS_PER_RUN:-3}" \
  --soak-sleep-ms "${TASK_076_SOAK_SLEEP_MS:-20}" \
  --latency-p95-ms "${TASK_076_LATENCY_P95_MS:-250}" \
  --latency-p99-ms "${TASK_076_LATENCY_P99_MS:-500}" \
  --success-ratio-min "${TASK_076_SUCCESS_RATIO_MIN:-0.99}" \
  --throughput-runs-per-sec-min "${TASK_076_THROUGHPUT_RUNS_PER_SEC_MIN:-2.0}"

echo "[task-076] running targeted regression tests"
(
  cd "$API_DIR"
  PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" -m pytest -q tests/test_api_slo_performance.py
) | tee "$PYTEST_LOG"

cp "$JSON_EVIDENCE" "$EVIDENCE_DIR/latest.json"
cp "$MD_EVIDENCE" "$EVIDENCE_DIR/latest.md"
cp "$PYTEST_LOG" "$EVIDENCE_DIR/latest-pytest.log"

echo "[task-076] evidence artifacts:"
echo "  - $JSON_EVIDENCE"
echo "  - $MD_EVIDENCE"
echo "  - $PYTEST_LOG"
