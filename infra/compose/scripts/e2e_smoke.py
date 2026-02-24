#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


API_BASE = os.getenv("E2E_API_BASE", "http://localhost:48000").rstrip("/")
TIMEOUT_SECONDS = int(os.getenv("E2E_TIMEOUT_SECONDS", "90"))


def _request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    url = f"{API_BASE}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = {}
        if body:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw": body}
        return exc.code, parsed


def _wait_for_health(path: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status, body = _request("GET", path)
        if status == 200 and body.get("status") == "ok":
            return
        time.sleep(1)
    raise TimeoutError(f"health check timed out: {path}")


def _wait_for_task_status(task_id: int, status_expected: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status, body = _request("GET", f"/tasks/{task_id}")
        if status == 200:
            current = body.get("status")
            if current == status_expected:
                return body
            if current in ("failed", "canceled", "submit-failed"):
                raise RuntimeError(f"task {task_id} reached terminal status={current}: {body}")
        time.sleep(0.5)
    raise TimeoutError(f"task {task_id} did not reach status={status_expected}")


def _wait_for_run_status(run_id: int, status_expected: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status, body = _request("GET", f"/workflow-runs/{run_id}")
        if status == 200 and body.get("status") == status_expected:
            return body
        time.sleep(0.5)
    raise TimeoutError(f"workflow run {run_id} did not reach status={status_expected}")


def main() -> int:
    print(f"[e2e] api base: {API_BASE}")
    _wait_for_health("/health", timeout_seconds=TIMEOUT_SECONDS)
    print("[e2e] api health: ok")

    role_status, role = _request(
        "POST",
        "/roles",
        {"name": "e2e-role", "context7_enabled": True},
    )
    if role_status != 200:
        raise RuntimeError(f"create role failed: {role_status} {role}")
    role_id = role["id"]
    print(f"[e2e] role created: {role_id}")

    workflow_status, workflow = _request(
        "POST",
        "/workflow-templates",
        {
            "name": "e2e-workflow",
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "E2E plan", "depends_on": []},
                {"step_id": "build", "role_id": role_id, "title": "E2E build", "depends_on": ["plan"]},
            ],
        },
    )
    if workflow_status != 200:
        raise RuntimeError(f"create workflow failed: {workflow_status} {workflow}")
    workflow_id = workflow["id"]
    print(f"[e2e] workflow created: {workflow_id}")

    run_status, run = _request(
        "POST",
        "/workflow-runs",
        {"workflow_template_id": workflow_id, "initiated_by": "e2e"},
    )
    if run_status != 200:
        raise RuntimeError(f"create run failed: {run_status} {run}")
    run_id = run["id"]
    print(f"[e2e] run created: {run_id} tasks={run.get('task_ids')}")

    # Two DAG steps: dispatch ready twice with wait for completion.
    for _ in range(2):
        dispatch_status, dispatch = _request("POST", f"/workflow-runs/{run_id}/dispatch-ready", {})
        if dispatch_status != 200:
            raise RuntimeError(f"dispatch-ready failed: {dispatch_status} {dispatch}")
        if dispatch.get("dispatched") is not True:
            raise RuntimeError(f"dispatch-ready returned no task: {dispatch}")
        task_id = int(dispatch["task_id"])
        print(f"[e2e] dispatched task: {task_id}")
        _wait_for_task_status(task_id, "success", timeout_seconds=TIMEOUT_SECONDS)
        print(f"[e2e] task success: {task_id}")

    final_run = _wait_for_run_status(run_id, "success", timeout_seconds=TIMEOUT_SECONDS)
    print(f"[e2e] run success: {final_run['id']}")
    print("[e2e] smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[e2e] failed: {exc}", file=sys.stderr)
        raise
