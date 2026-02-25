#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
EVIDENCE_DIR="${TASK_072_EVIDENCE_DIR:-$ROOT_DIR/docs/evidence/task-072}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -n "${API_PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$API_PYTHON_BIN"
elif [[ -x "$API_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$API_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

mkdir -p "$EVIDENCE_DIR"

JSON_EVIDENCE="$EVIDENCE_DIR/task-072-concurrency-stress-$TIMESTAMP.json"
MD_EVIDENCE="$EVIDENCE_DIR/task-072-concurrency-stress-$TIMESTAMP.md"
PYTEST_LOG="$EVIDENCE_DIR/task-072-pytest-$TIMESTAMP.log"

echo "[task-072] using python: $PYTHON_BIN"

echo "[task-072] running concurrency stress harness"
PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" "$API_DIR/scripts/task_072_concurrency_stress.py" \
  --output-json "$JSON_EVIDENCE" \
  --output-md "$MD_EVIDENCE" \
  --dispatch-iterations "${TASK_072_DISPATCH_ITERATIONS:-4}" \
  --dispatch-parallelism "${TASK_072_DISPATCH_PARALLELISM:-8}" \
  --dispatch-task-count "${TASK_072_DISPATCH_TASK_COUNT:-12}" \
  --rerun-iterations "${TASK_072_RERUN_ITERATIONS:-4}" \
  --rerun-parallelism "${TASK_072_RERUN_PARALLELISM:-8}" \
  --rerun-attempts "${TASK_072_RERUN_ATTEMPTS:-16}" \
  --approval-iterations "${TASK_072_APPROVAL_ITERATIONS:-4}" \
  --approval-parallelism "${TASK_072_APPROVAL_PARALLELISM:-8}" \
  --approval-attempts "${TASK_072_APPROVAL_ATTEMPTS:-50}"

echo "[task-072] running targeted regression tests"
(
  cd "$API_DIR"
  PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" -m pytest -q tests/test_api_concurrency_stress.py
) | tee "$PYTEST_LOG"

cp "$JSON_EVIDENCE" "$EVIDENCE_DIR/latest.json"
cp "$MD_EVIDENCE" "$EVIDENCE_DIR/latest.md"
cp "$PYTEST_LOG" "$EVIDENCE_DIR/latest-pytest.log"

echo "[task-072] evidence artifacts:"
echo "  - $JSON_EVIDENCE"
echo "  - $MD_EVIDENCE"
echo "  - $PYTEST_LOG"
