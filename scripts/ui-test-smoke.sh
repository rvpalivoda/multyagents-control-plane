#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/apps/ui"

if ! command -v timeout >/dev/null 2>&1; then
  echo "missing required command: timeout" >&2
  exit 1
fi

VITEST_BIN="$ROOT_DIR/apps/ui/node_modules/.bin/vitest"
if [[ ! -x "$VITEST_BIN" ]]; then
  echo "missing local vitest binary: $VITEST_BIN" >&2
  echo "install UI dependencies first: cd apps/ui && npm ci" >&2
  exit 1
fi

# Run key suites with deterministic single-fork execution and hard timeout.
timeout --foreground --signal=TERM --kill-after=10s 180s \
  "$VITEST_BIN" run \
  --reporter=basic \
  --no-file-parallelism \
  --pool=forks \
  --poolOptions.forks.singleFork=true \
  src/components/workflowEditorUtils.test.ts \
  src/App.workflowBuilder.test.tsx
