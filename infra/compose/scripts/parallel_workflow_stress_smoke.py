#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


API_BASE = os.getenv("STRESS_API_BASE", "http://localhost:48000").rstrip("/")


def _int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid integer for {name}: {raw}") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


RUN_COUNT = _int_env("STRESS_RUNS", 20)
PARALLELISM = _int_env("STRESS_PARALLELISM", 6)
RUN_TIMEOUT_SECONDS = _int_env("STRESS_RUN_TIMEOUT_SECONDS", 90)
HEALTH_TIMEOUT_SECONDS = _int_env("STRESS_HEALTH_TIMEOUT_SECONDS", 90)
MAX_IDLE_CYCLES = _int_env("STRESS_MAX_IDLE_CYCLES", 40)

POLL_INTERVAL_SECONDS = float(os.getenv("STRESS_POLL_INTERVAL_SECONDS", "0.05"))
if POLL_INTERVAL_SECONDS <= 0:
    raise ValueError("STRESS_POLL_INTERVAL_SECONDS must be > 0")

OUTPUT_JSON_PATH = os.getenv("STRESS_OUTPUT_JSON", "").strip()
INITIATED_BY = os.getenv("STRESS_INITIATED_BY", "parallel-stress-smoke")


@dataclass
class RunResult:
    run_id: int
    status: str
    duration_seconds: float
    dispatch_calls: int
    status_updates: int
    reason_counts: dict[str, int]
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 4),
            "dispatch_calls": self.dispatch_calls,
            "status_updates": self.status_updates,
            "reason_counts": self.reason_counts,
            "error": self.error,
        }


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = f"{API_BASE}{path}"
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8")
            parsed = json.loads(content) if content else {}
            if not isinstance(parsed, dict):
                return response.getcode(), {"value": parsed}
            return response.getcode(), parsed
    except urllib.error.HTTPError as exc:
        content = exc.read().decode("utf-8")
        parsed: dict[str, Any] = {}
        if content:
            try:
                decoded = json.loads(content)
                if isinstance(decoded, dict):
                    parsed = decoded
                else:
                    parsed = {"value": decoded}
            except json.JSONDecodeError:
                parsed = {"raw": content}
        return exc.code, parsed


def _wait_for_health(path: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status, body = _request("GET", path)
        if status == 200 and body.get("status") == "ok":
            return
        time.sleep(1)
    raise TimeoutError(f"health check timed out: {path}")


def _create_role() -> int:
    suffix = int(time.time() * 1000)
    status, body = _request(
        "POST",
        "/roles",
        {"name": f"stress-role-{suffix}", "context7_enabled": True},
    )
    if status != 200:
        raise RuntimeError(f"create role failed: HTTP {status} {body}")
    role_id = body.get("id")
    if not isinstance(role_id, int):
        raise RuntimeError(f"create role failed: invalid role id in response: {body}")
    return role_id


def _create_workflow(role_id: int) -> int:
    suffix = int(time.time() * 1000)
    status, body = _request(
        "POST",
        "/workflow-templates",
        {
            "name": f"parallel-stress-{suffix}",
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Stress Plan", "depends_on": []},
                {"step_id": "build", "role_id": role_id, "title": "Stress Build", "depends_on": ["plan"]},
                {"step_id": "test", "role_id": role_id, "title": "Stress Test", "depends_on": ["plan"]},
                {
                    "step_id": "report",
                    "role_id": role_id,
                    "title": "Stress Report",
                    "depends_on": ["build", "test"],
                },
            ],
        },
    )
    if status != 200:
        raise RuntimeError(f"create workflow failed: HTTP {status} {body}")
    workflow_id = body.get("id")
    if not isinstance(workflow_id, int):
        raise RuntimeError(f"create workflow failed: invalid workflow id in response: {body}")
    return workflow_id


def _create_runs(workflow_id: int, run_count: int) -> list[int]:
    run_ids: list[int] = []
    for index in range(run_count):
        status, body = _request(
            "POST",
            "/workflow-runs",
            {
                "workflow_template_id": workflow_id,
                "initiated_by": f"{INITIATED_BY}-{index}",
            },
        )
        if status != 200:
            raise RuntimeError(f"create run failed at index {index}: HTTP {status} {body}")
        run_id = body.get("id")
        if not isinstance(run_id, int):
            raise RuntimeError(f"create run failed at index {index}: invalid run id in response: {body}")
        run_ids.append(run_id)
    return run_ids


def _run_to_success(run_id: int) -> RunResult:
    started = time.perf_counter()
    dispatch_calls = 0
    status_updates = 0
    reason_counts: dict[str, int] = {}
    idle_cycles = 0

    deadline = time.perf_counter() + RUN_TIMEOUT_SECONDS
    while time.perf_counter() < deadline:
        run_status_code, run_body = _request("GET", f"/workflow-runs/{run_id}")
        if run_status_code != 200:
            duration = time.perf_counter() - started
            return RunResult(
                run_id=run_id,
                status="failed",
                duration_seconds=duration,
                dispatch_calls=dispatch_calls,
                status_updates=status_updates,
                reason_counts=reason_counts,
                error=f"read run failed: HTTP {run_status_code} {run_body}",
            )

        run_status = str(run_body.get("status"))
        if run_status == "success":
            duration = time.perf_counter() - started
            return RunResult(
                run_id=run_id,
                status="success",
                duration_seconds=duration,
                dispatch_calls=dispatch_calls,
                status_updates=status_updates,
                reason_counts=reason_counts,
            )
        if run_status in ("failed", "aborted"):
            duration = time.perf_counter() - started
            return RunResult(
                run_id=run_id,
                status="failed",
                duration_seconds=duration,
                dispatch_calls=dispatch_calls,
                status_updates=status_updates,
                reason_counts=reason_counts,
                error=f"run reached terminal non-success status={run_status}",
            )

        dispatch_status, dispatch_body = _request("POST", f"/workflow-runs/{run_id}/dispatch-ready", {})
        if dispatch_status != 200:
            duration = time.perf_counter() - started
            return RunResult(
                run_id=run_id,
                status="failed",
                duration_seconds=duration,
                dispatch_calls=dispatch_calls,
                status_updates=status_updates,
                reason_counts=reason_counts,
                error=f"dispatch-ready failed: HTTP {dispatch_status} {dispatch_body}",
            )

        dispatch_calls += 1
        if dispatch_body.get("dispatched") is True:
            idle_cycles = 0
            task_id = dispatch_body.get("task_id")
            if not isinstance(task_id, int):
                duration = time.perf_counter() - started
                return RunResult(
                    run_id=run_id,
                    status="failed",
                    duration_seconds=duration,
                    dispatch_calls=dispatch_calls,
                    status_updates=status_updates,
                    reason_counts=reason_counts,
                    error=f"dispatch response missing integer task_id: {dispatch_body}",
                )

            update_status, update_body = _request(
                "POST",
                f"/runner/tasks/{task_id}/status",
                {"status": "success", "message": "parallel stress smoke success"},
            )
            if update_status != 200:
                duration = time.perf_counter() - started
                return RunResult(
                    run_id=run_id,
                    status="failed",
                    duration_seconds=duration,
                    dispatch_calls=dispatch_calls,
                    status_updates=status_updates,
                    reason_counts=reason_counts,
                    error=f"runner status update failed for task {task_id}: HTTP {update_status} {update_body}",
                )
            status_updates += 1
            time.sleep(random.uniform(0.001, 0.01))
            continue

        idle_cycles += 1
        reason = str(dispatch_body.get("reason") or "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if idle_cycles >= MAX_IDLE_CYCLES:
            final_status_code, final_body = _request("GET", f"/workflow-runs/{run_id}")
            if final_status_code == 200 and final_body.get("status") == "success":
                duration = time.perf_counter() - started
                return RunResult(
                    run_id=run_id,
                    status="success",
                    duration_seconds=duration,
                    dispatch_calls=dispatch_calls,
                    status_updates=status_updates,
                    reason_counts=reason_counts,
                )
            duration = time.perf_counter() - started
            return RunResult(
                run_id=run_id,
                status="failed",
                duration_seconds=duration,
                dispatch_calls=dispatch_calls,
                status_updates=status_updates,
                reason_counts=reason_counts,
                error=f"run stuck without dispatch progress after {idle_cycles} cycles",
            )
        time.sleep(POLL_INTERVAL_SECONDS)

    duration = time.perf_counter() - started
    return RunResult(
        run_id=run_id,
        status="failed",
        duration_seconds=duration,
        dispatch_calls=dispatch_calls,
        status_updates=status_updates,
        reason_counts=reason_counts,
        error=f"run timeout after {RUN_TIMEOUT_SECONDS}s",
    )


def _write_summary(path: str, summary: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    print(
        "[stress] config: "
        f"api={API_BASE} runs={RUN_COUNT} parallelism={PARALLELISM} "
        f"run_timeout={RUN_TIMEOUT_SECONDS}s poll_interval={POLL_INTERVAL_SECONDS}s"
    )

    _wait_for_health("/health", timeout_seconds=HEALTH_TIMEOUT_SECONDS)
    print("[stress] api health: ok")

    role_id = _create_role()
    workflow_id = _create_workflow(role_id)
    run_ids = _create_runs(workflow_id, RUN_COUNT)
    print(f"[stress] prepared role={role_id} workflow={workflow_id} runs={len(run_ids)}")

    started = time.perf_counter()
    results: list[RunResult] = []
    with ThreadPoolExecutor(max_workers=PARALLELISM) as pool:
        futures = [pool.submit(_run_to_success, run_id) for run_id in run_ids]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                "[stress] run complete: "
                f"run_id={result.run_id} status={result.status} "
                f"dispatch_calls={result.dispatch_calls} status_updates={result.status_updates} "
                f"duration={result.duration_seconds:.2f}s"
            )

    wall_seconds = time.perf_counter() - started

    success_results = [item for item in results if item.status == "success"]
    failed_results = [item for item in results if item.status != "success"]
    durations = [item.duration_seconds for item in results]

    reason_totals: dict[str, int] = {}
    for result in results:
        for reason, count in result.reason_counts.items():
            reason_totals[reason] = reason_totals.get(reason, 0) + count

    summary: dict[str, Any] = {
        "config": {
            "api_base": API_BASE,
            "runs": RUN_COUNT,
            "parallelism": PARALLELISM,
            "run_timeout_seconds": RUN_TIMEOUT_SECONDS,
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            "max_idle_cycles": MAX_IDLE_CYCLES,
        },
        "prepared": {
            "role_id": role_id,
            "workflow_id": workflow_id,
            "run_ids": run_ids,
        },
        "summary": {
            "overall_status": "success" if not failed_results else "failed",
            "requested_runs": RUN_COUNT,
            "completed_runs": len(results),
            "success": len(success_results),
            "failed": len(failed_results),
            "total_dispatch_calls": sum(item.dispatch_calls for item in results),
            "total_runner_status_updates": sum(item.status_updates for item in results),
            "wall_seconds": round(wall_seconds, 4),
            "avg_run_seconds": round(mean(durations), 4) if durations else 0.0,
            "max_run_seconds": round(max(durations), 4) if durations else 0.0,
            "reasons": reason_totals,
        },
        "failures": [item.as_dict() for item in failed_results],
    }

    print("[stress] summary")
    print(
        "[stress] "
        f"overall={summary['summary']['overall_status']} "
        f"requested={summary['summary']['requested_runs']} "
        f"completed={summary['summary']['completed_runs']} "
        f"success={summary['summary']['success']} "
        f"failed={summary['summary']['failed']}"
    )
    print(
        "[stress] "
        f"dispatch_calls={summary['summary']['total_dispatch_calls']} "
        f"runner_status_updates={summary['summary']['total_runner_status_updates']} "
        f"wall_seconds={summary['summary']['wall_seconds']} "
        f"avg_run_seconds={summary['summary']['avg_run_seconds']}"
    )
    if summary["summary"]["reasons"]:
        print(f"[stress] blocked reasons: {summary['summary']['reasons']}")

    if failed_results:
        print("[stress] failures:")
        for failed in failed_results[:10]:
            print(
                "[stress] "
                f"run_id={failed.run_id} error={failed.error} "
                f"dispatch_calls={failed.dispatch_calls} reason_counts={failed.reason_counts}"
            )

    if OUTPUT_JSON_PATH:
        _write_summary(OUTPUT_JSON_PATH, summary)
        print(f"[stress] summary json: {OUTPUT_JSON_PATH}")

    if failed_results:
        return 1
    print("[stress] smoke passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[stress] failed: {exc}", file=sys.stderr)
        raise
