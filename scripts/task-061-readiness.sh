#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
EVIDENCE_DIR="${TASK_061_EVIDENCE_DIR:-$ROOT_DIR/docs/evidence/task-061}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -n "${API_PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$API_PYTHON_BIN"
elif [[ -x "$API_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$API_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

mkdir -p "$EVIDENCE_DIR"

JSON_EVIDENCE="$EVIDENCE_DIR/task-061-local-readiness-$TIMESTAMP.json"
MD_EVIDENCE="$EVIDENCE_DIR/task-061-local-readiness-$TIMESTAMP.md"
PYTEST_LOG="$EVIDENCE_DIR/task-061-pytest-$TIMESTAMP.log"

echo "[task-061] using python: $PYTHON_BIN"

echo "[task-061] running local readiness scenario harness"
PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" "$API_DIR/scripts/task_061_local_readiness.py" \
  --initiated-by "task-061-script" \
  --output-json "$JSON_EVIDENCE" \
  --output-md "$MD_EVIDENCE"

echo "[task-061] running targeted regression tests"
(
  cd "$API_DIR"
  PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" -m pytest -q tests/test_local_readiness_scenarios.py
) | tee "$PYTEST_LOG"

cp "$JSON_EVIDENCE" "$EVIDENCE_DIR/latest.json"
cp "$MD_EVIDENCE" "$EVIDENCE_DIR/latest.md"
cp "$PYTEST_LOG" "$EVIDENCE_DIR/latest-pytest.log"

echo "[task-061] evidence artifacts:"
echo "  - $JSON_EVIDENCE"
echo "  - $MD_EVIDENCE"
echo "  - $PYTEST_LOG"
