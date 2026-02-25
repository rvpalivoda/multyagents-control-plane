#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
EVIDENCE_DIR="${TASK_073_EVIDENCE_DIR:-$ROOT_DIR/docs/evidence/task-073}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -n "${API_PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$API_PYTHON_BIN"
elif [[ -x "$API_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$API_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

mkdir -p "$EVIDENCE_DIR"

JSON_EVIDENCE="$EVIDENCE_DIR/task-073-restart-persistence-$TIMESTAMP.json"
MD_EVIDENCE="$EVIDENCE_DIR/task-073-restart-persistence-$TIMESTAMP.md"
PYTEST_LOG="$EVIDENCE_DIR/task-073-pytest-$TIMESTAMP.log"

echo "[task-073] using python: $PYTHON_BIN"

echo "[task-073] running restart persistence invariant suite"
PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" "$API_DIR/scripts/task_073_restart_persistence.py" \
  --output-json "$JSON_EVIDENCE" \
  --output-md "$MD_EVIDENCE" \
  --callback-replays "${TASK_073_CALLBACK_REPLAYS:-2}"

echo "[task-073] running targeted regression tests"
(
  cd "$API_DIR"
  PYTHONPATH="$API_DIR/src" "$PYTHON_BIN" -m pytest -q tests/test_api_restart_persistence.py
) | tee "$PYTEST_LOG"

cp "$JSON_EVIDENCE" "$EVIDENCE_DIR/latest.json"
cp "$MD_EVIDENCE" "$EVIDENCE_DIR/latest.md"
cp "$PYTEST_LOG" "$EVIDENCE_DIR/latest-pytest.log"

echo "[task-073] evidence artifacts:"
echo "  - $JSON_EVIDENCE"
echo "  - $MD_EVIDENCE"
echo "  - $PYTEST_LOG"
