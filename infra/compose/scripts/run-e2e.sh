#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE_DIR="$ROOT_DIR/infra/compose"
RUNNER_DIR="$ROOT_DIR/apps/host-runner"

HOST_RUNNER_PORT="${HOST_RUNNER_PORT:-48070}"
HOST_RUNNER_URL="http://127.0.0.1:${HOST_RUNNER_PORT}"
RUNNER_LOG="${RUNNER_LOG:-/tmp/multyagents-host-runner.log}"

cleanup() {
  set +e
  if [[ -n "${RUNNER_PID:-}" ]] && kill -0 "$RUNNER_PID" 2>/dev/null; then
    kill "$RUNNER_PID" >/dev/null 2>&1 || true
    wait "$RUNNER_PID" 2>/dev/null || true
  fi
  (cd "$COMPOSE_DIR" && docker compose down --remove-orphans) >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [[ ! -x "$RUNNER_DIR/.venv/bin/python" ]]; then
  python3 -m venv "$RUNNER_DIR/.venv"
  "$RUNNER_DIR/.venv/bin/pip" install -e "$RUNNER_DIR"
fi

echo "[e2e] starting host-runner on ${HOST_RUNNER_URL}"
(
  cd "$RUNNER_DIR"
  export HOST_RUNNER_EXECUTOR=mock
  export HOST_RUNNER_CLEANUP_WORKTREE=true
  exec "$RUNNER_DIR/.venv/bin/uvicorn" multyagents_host_runner.main:app --host 0.0.0.0 --port "$HOST_RUNNER_PORT"
) >"$RUNNER_LOG" 2>&1 &
RUNNER_PID=$!

echo "[e2e] starting docker compose stack"
(cd "$COMPOSE_DIR" && docker compose up --build -d)

echo "[e2e] running smoke scenario"
E2E_API_BASE="${E2E_API_BASE:-http://localhost:48000}" \
E2E_TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS:-90}" \
python3 "$COMPOSE_DIR/scripts/e2e_smoke.py"

echo "[e2e] completed successfully"
