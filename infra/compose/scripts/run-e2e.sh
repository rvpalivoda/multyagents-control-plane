#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE_DIR="$ROOT_DIR/infra/compose"
RUNNER_DIR="$ROOT_DIR/apps/host-runner"

HOST_RUNNER_PORT_DEFAULT=48070
HOST_RUNNER_PORT_MAX=48090
HOST_RUNNER_PORT="${HOST_RUNNER_PORT:-$HOST_RUNNER_PORT_DEFAULT}"
HOST_RUNNER_URL=""
RUNNER_LOG="${RUNNER_LOG:-/tmp/multyagents-host-runner.log}"

is_port_busy() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${port}$"
    return $?
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

resolve_runner_port() {
  if [[ "${HOST_RUNNER_PORT}" != "$HOST_RUNNER_PORT_DEFAULT" ]]; then
    if is_port_busy "$HOST_RUNNER_PORT"; then
      echo "[e2e] error: HOST_RUNNER_PORT=${HOST_RUNNER_PORT} is already in use" >&2
      exit 1
    fi
    return
  fi

  if ! is_port_busy "$HOST_RUNNER_PORT_DEFAULT"; then
    HOST_RUNNER_PORT="$HOST_RUNNER_PORT_DEFAULT"
    return
  fi

  for candidate in $(seq $((HOST_RUNNER_PORT_DEFAULT + 1)) "$HOST_RUNNER_PORT_MAX"); do
    if ! is_port_busy "$candidate"; then
      HOST_RUNNER_PORT="$candidate"
      echo "[e2e] default port ${HOST_RUNNER_PORT_DEFAULT} is busy, using ${HOST_RUNNER_PORT}"
      return
    fi
  done

  echo "[e2e] error: no free host-runner port in range ${HOST_RUNNER_PORT_DEFAULT}-${HOST_RUNNER_PORT_MAX}" >&2
  exit 1
}

cleanup() {
  set +e
  if [[ -n "${RUNNER_PID:-}" ]] && kill -0 "$RUNNER_PID" 2>/dev/null; then
    kill "$RUNNER_PID" >/dev/null 2>&1 || true
    wait "$RUNNER_PID" 2>/dev/null || true
  fi
  (cd "$COMPOSE_DIR" && docker compose down --remove-orphans) >/dev/null 2>&1 || true
}
trap cleanup EXIT

resolve_runner_port
HOST_RUNNER_URL="http://127.0.0.1:${HOST_RUNNER_PORT}"
export API_HOST_RUNNER_URL="${API_HOST_RUNNER_URL:-http://host.docker.internal:${HOST_RUNNER_PORT}}"

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
