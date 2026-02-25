from __future__ import annotations

import itertools
import math
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from multyagents_api.schemas import RunnerSubmission, RunnerSubmitPayload, TaskStatus, WorkflowRunStatus
from multyagents_api.store import InMemoryStore

_name_seq = itertools.count(1)


@dataclass(frozen=True)
class SloPerformanceConfig:
    load_runs: int = 16
    soak_runs: int = 60
    steps_per_run: int = 3
    soak_sleep_ms: int = 20


@dataclass(frozen=True)
class SloThresholds:
    latency_p95_ms: float = 250.0
    latency_p99_ms: float = 500.0
    success_ratio_min: float = 0.99
    throughput_runs_per_sec_min: float = 2.0


def run_slo_performance_suite(
    config: SloPerformanceConfig | None = None,
    thresholds: SloThresholds | None = None,
) -> dict[str, Any]:
    cfg = config or SloPerformanceConfig()
    limits = thresholds or SloThresholds()
    _validate_config(cfg, limits)

    with _isolated_api_client() as client:
        load_scenario = _run_scenario(
            client,
            name="load-burst",
            objective=(
                "Short burst load keeps workflow run path within latency/success/throughput SLO thresholds."
            ),
            run_count=cfg.load_runs,
            steps_per_run=cfg.steps_per_run,
            inter_run_sleep_ms=0,
            thresholds=limits,
        )
        soak_scenario = _run_scenario(
            client,
            name="sustained-soak",
            objective=(
                "Sustained repeated workflow runs remain stable with bounded latency and no success-ratio drift."
            ),
            run_count=cfg.soak_runs,
            steps_per_run=cfg.steps_per_run,
            inter_run_sleep_ms=cfg.soak_sleep_ms,
            thresholds=limits,
        )

    scenarios = [load_scenario, soak_scenario]
    checks_total = sum(len(scenario["checks"]) for scenario in scenarios)
    checks_passed = sum(
        1
        for scenario in scenarios
        for check in scenario["checks"]
        if check["passed"]
    )
    overall_status = "pass" if checks_total == checks_passed else "fail"

    return {
        "task": "TASK-076",
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "config": {
            "load_runs": cfg.load_runs,
            "soak_runs": cfg.soak_runs,
            "steps_per_run": cfg.steps_per_run,
            "soak_sleep_ms": cfg.soak_sleep_ms,
        },
        "thresholds": {
            "latency_p95_ms": limits.latency_p95_ms,
            "latency_p99_ms": limits.latency_p99_ms,
            "success_ratio_min": limits.success_ratio_min,
            "throughput_runs_per_sec_min": limits.throughput_runs_per_sec_min,
        },
        "summary": {
            "scenario_count": len(scenarios),
            "checks_total": checks_total,
            "checks_passed": checks_passed,
            "overall_status": overall_status,
        },
        "scenarios": scenarios,
    }


def _run_scenario(
    client: TestClient,
    *,
    name: str,
    objective: str,
    run_count: int,
    steps_per_run: int,
    inter_run_sleep_ms: int,
    thresholds: SloThresholds,
) -> dict[str, Any]:
    scenario_started = time.perf_counter()
    failures: Counter[str] = Counter()
    endpoint_latencies: dict[str, list[float]] = {
        "workflow_run_create": [],
        "dispatch_ready": [],
        "runner_status": [],
        "workflow_run_read": [],
    }
    requests_total = 0
    successful_runs = 0
    dispatched_tasks_total = 0

    role_id = _create_role(client, f"task-076-{name}-role")
    workflow_id = _create_workflow(
        client,
        workflow_name_prefix=f"task-076-{name}-workflow",
        role_id=role_id,
        steps_per_run=steps_per_run,
    )

    for run_index in range(run_count):
        result = _execute_workflow_run(
            client,
            workflow_id=workflow_id,
            initiated_by=f"task-076-{name}-{run_index + 1}",
            steps_per_run=steps_per_run,
        )
        requests_total += result["requests_total"]
        dispatched_tasks_total += result["dispatched_tasks"]

        for endpoint_name, samples in result["endpoint_latencies"].items():
            endpoint_latencies[endpoint_name].extend(samples)

        if result["success"]:
            successful_runs += 1
        else:
            failures[result["failure_reason"]] += 1

        if inter_run_sleep_ms > 0:
            time.sleep(inter_run_sleep_ms / 1000.0)

    duration_seconds = max(time.perf_counter() - scenario_started, 1e-9)
    all_latencies = [value for samples in endpoint_latencies.values() for value in samples]

    metrics = {
        "run_count": run_count,
        "steps_per_run": steps_per_run,
        "successful_runs": successful_runs,
        "failed_runs": run_count - successful_runs,
        "success_ratio": successful_runs / run_count if run_count else 0.0,
        "requests_total": requests_total,
        "dispatched_tasks_total": dispatched_tasks_total,
        "duration_ms": int(duration_seconds * 1000),
        "throughput_runs_per_sec": successful_runs / duration_seconds,
        "throughput_requests_per_sec": requests_total / duration_seconds,
        "latency_ms": _latency_summary(all_latencies),
        "endpoint_latency_ms": {
            endpoint: _latency_summary(samples) for endpoint, samples in endpoint_latencies.items()
        },
        "failure_counts": {key: value for key, value in sorted(failures.items())},
    }

    checks = [
        _check_threshold(
            check_id="latency-p95",
            description="Combined API request latency p95 stays within threshold.",
            operator="<=",
            threshold=thresholds.latency_p95_ms,
            actual=metrics["latency_ms"]["p95"],
        ),
        _check_threshold(
            check_id="latency-p99",
            description="Combined API request latency p99 stays within threshold.",
            operator="<=",
            threshold=thresholds.latency_p99_ms,
            actual=metrics["latency_ms"]["p99"],
        ),
        _check_threshold(
            check_id="success-ratio",
            description="Workflow run success ratio meets minimum threshold.",
            operator=">=",
            threshold=thresholds.success_ratio_min,
            actual=metrics["success_ratio"],
        ),
        _check_threshold(
            check_id="throughput-runs-per-sec",
            description="Workflow run throughput meets minimum threshold.",
            operator=">=",
            threshold=thresholds.throughput_runs_per_sec_min,
            actual=metrics["throughput_runs_per_sec"],
        ),
    ]

    scenario_status = "pass" if all(check["passed"] for check in checks) else "fail"
    return {
        "name": name,
        "objective": objective,
        "status": scenario_status,
        "checks": checks,
        "metrics": metrics,
    }


def _execute_workflow_run(
    client: TestClient,
    *,
    workflow_id: int,
    initiated_by: str,
    steps_per_run: int,
) -> dict[str, Any]:
    endpoint_latencies: dict[str, list[float]] = {
        "workflow_run_create": [],
        "dispatch_ready": [],
        "runner_status": [],
        "workflow_run_read": [],
    }
    requests_total = 0
    dispatched_tasks = 0

    try:
        run, latency_ms = _request_json(
            client,
            "POST",
            "/workflow-runs",
            payload={
                "workflow_template_id": workflow_id,
                "initiated_by": initiated_by,
            },
            expected_status=200,
        )
        endpoint_latencies["workflow_run_create"].append(latency_ms)
        requests_total += 1
        run_id = int(run["id"])

        for _ in range(steps_per_run):
            dispatch_body, dispatch_latency_ms = _request_json(
                client,
                "POST",
                f"/workflow-runs/{run_id}/dispatch-ready",
                payload={},
                expected_status=200,
            )
            endpoint_latencies["dispatch_ready"].append(dispatch_latency_ms)
            requests_total += 1

            if dispatch_body.get("dispatched") is not True:
                reason = str(dispatch_body.get("reason") or "dispatch-ready returned no task")
                return {
                    "success": False,
                    "failure_reason": reason,
                    "endpoint_latencies": endpoint_latencies,
                    "requests_total": requests_total,
                    "dispatched_tasks": dispatched_tasks,
                }

            task_id = int(dispatch_body["task_id"])
            _, status_latency_ms = _request_json(
                client,
                "POST",
                f"/runner/tasks/{task_id}/status",
                payload={
                    "status": "success",
                    "message": "task-076 benchmark synthetic success",
                },
                expected_status=200,
            )
            endpoint_latencies["runner_status"].append(status_latency_ms)
            requests_total += 1
            dispatched_tasks += 1

        run_final, final_latency_ms = _request_json(
            client,
            "GET",
            f"/workflow-runs/{run_id}",
            payload=None,
            expected_status=200,
        )
        endpoint_latencies["workflow_run_read"].append(final_latency_ms)
        requests_total += 1

        if str(run_final.get("status")) != WorkflowRunStatus.SUCCESS.value:
            return {
                "success": False,
                "failure_reason": f"final run status={run_final.get('status')}",
                "endpoint_latencies": endpoint_latencies,
                "requests_total": requests_total,
                "dispatched_tasks": dispatched_tasks,
            }

        return {
            "success": True,
            "failure_reason": "",
            "endpoint_latencies": endpoint_latencies,
            "requests_total": requests_total,
            "dispatched_tasks": dispatched_tasks,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "failure_reason": f"exception: {exc}",
            "endpoint_latencies": endpoint_latencies,
            "requests_total": requests_total,
            "dispatched_tasks": dispatched_tasks,
        }


def _create_role(client: TestClient, name_prefix: str) -> int:
    role_name = f"{name_prefix}-{next(_name_seq)}"
    body, _ = _request_json(
        client,
        "POST",
        "/roles",
        payload={
            "name": role_name,
            "context7_enabled": True,
        },
        expected_status=200,
    )
    return int(body["id"])


def _create_workflow(
    client: TestClient,
    *,
    workflow_name_prefix: str,
    role_id: int,
    steps_per_run: int,
) -> int:
    steps: list[dict[str, Any]] = []
    for index in range(steps_per_run):
        step_id = f"step-{index + 1}"
        depends_on = [f"step-{index}"] if index > 0 else []
        steps.append(
            {
                "step_id": step_id,
                "role_id": role_id,
                "title": f"TASK-076 {step_id}",
                "depends_on": depends_on,
            }
        )

    workflow_name = f"{workflow_name_prefix}-{next(_name_seq)}"
    body, _ = _request_json(
        client,
        "POST",
        "/workflow-templates",
        payload={
            "name": workflow_name,
            "steps": steps,
        },
        expected_status=200,
    )
    return int(body["id"])


def _request_json(
    client: TestClient,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None,
    expected_status: int,
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    if payload is None:
        response = client.request(method, path)
    else:
        response = client.request(method, path, json=payload)
    latency_ms = (time.perf_counter() - started) * 1000.0
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{method} {path}: expected HTTP {expected_status}, got {response.status_code} body={response.text}"
        )
    return response.json(), latency_ms


def _latency_summary(samples: list[float]) -> dict[str, int | float]:
    if not samples:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "avg": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }

    return {
        "count": len(samples),
        "min": round(min(samples), 3),
        "max": round(max(samples), 3),
        "avg": round(sum(samples) / len(samples), 3),
        "p95": round(_percentile(samples, 95), 3),
        "p99": round(_percentile(samples, 99), 3),
    }


def _percentile(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    if len(ordered) == 1:
        return float(ordered[0])

    rank = (percentile / 100.0) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(ordered[lower])
    ratio = rank - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * ratio)


def _check_threshold(
    *,
    check_id: str,
    description: str,
    operator: str,
    threshold: float,
    actual: float,
) -> dict[str, Any]:
    if operator == "<=":
        passed = actual <= threshold
    elif operator == ">=":
        passed = actual >= threshold
    else:
        raise ValueError(f"unsupported operator: {operator}")

    return {
        "id": check_id,
        "description": description,
        "operator": operator,
        "threshold": threshold,
        "actual": actual,
        "passed": passed,
    }


def _validate_config(config: SloPerformanceConfig, thresholds: SloThresholds) -> None:
    if min(config.load_runs, config.soak_runs, config.steps_per_run) < 1:
        raise ValueError("load_runs, soak_runs, and steps_per_run must be >= 1")
    if config.soak_sleep_ms < 0:
        raise ValueError("soak_sleep_ms must be >= 0")

    if thresholds.latency_p95_ms <= 0 or thresholds.latency_p99_ms <= 0:
        raise ValueError("latency thresholds must be > 0")
    if thresholds.success_ratio_min <= 0 or thresholds.success_ratio_min > 1:
        raise ValueError("success_ratio_min must be in (0, 1]")
    if thresholds.throughput_runs_per_sec_min <= 0:
        raise ValueError("throughput_runs_per_sec_min must be > 0")


@contextmanager
def _isolated_api_client() -> Any:
    from multyagents_api import main as api_main

    original_store = api_main.store
    original_submit_to_runner = api_main.submit_to_runner

    def _stub_submit(_: RunnerSubmitPayload) -> RunnerSubmission:
        return RunnerSubmission(
            submitted=True,
            runner_url="stub://task-076",
            runner_task_status=TaskStatus.QUEUED.value,
            message="queued by task-076 performance suite",
        )

    api_main.store = InMemoryStore()
    api_main.submit_to_runner = _stub_submit
    client = TestClient(api_main.app)
    try:
        yield client
    finally:
        client.close()
        api_main.store = original_store
        api_main.submit_to_runner = original_submit_to_runner
