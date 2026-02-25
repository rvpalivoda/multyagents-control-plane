#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/apps/ui"

# Run key suites with hard timeout to avoid hanging process edge-cases.
timeout --signal=TERM 180s npx vitest run src/components/workflowEditorUtils.test.ts src/App.workflowBuilder.test.tsx --reporter=basic
