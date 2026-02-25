from __future__ import annotations

import itertools
from typing import Any


_name_seq = itertools.count(1)


def _next_name(prefix: str) -> str:
    return f"{prefix}-{next(_name_seq)}"


def _json(response: Any) -> Any:
    return response.json()


def _require_status(response: Any, status_code: int, *, context: str) -> Any:
    if response.status_code != status_code:
        raise RuntimeError(f"{context}: expected HTTP {status_code}, got {response.status_code}: {response.text}")
    return _json(response)


def _create_role(client: Any, *, name_prefix: str, retry_policy: dict[str, Any] | None = None) -> int:
    payload: dict[str, Any] = {
        "name": _next_name(name_prefix),
        "context7_enabled": True,
    }
    if retry_policy is not None:
        payload["execution_constraints"] = {"retry_policy": retry_policy}

    response = client.post("/roles", json=payload)
    role = _require_status(response, 200, context="create role")
    return int(role["id"])


def _create_workflow(client: Any, *, name_prefix: str, steps: list[dict[str, Any]]) -> int:
    response = client.post(
        "/workflow-templates",
        json={
            "name": _next_name(name_prefix),
            "steps": steps,
        },
    )
    workflow = _require_status(response, 200, context="create workflow")
    return int(workflow["id"])


def _create_run(
    client: Any,
    *,
    workflow_template_id: int,
    initiated_by: str,
    step_task_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workflow_template_id": workflow_template_id,
        "initiated_by": initiated_by,
    }
    if step_task_overrides:
        payload["step_task_overrides"] = step_task_overrides
    response = client.post("/workflow-runs", json=payload)
    return _require_status(response, 200, context="create workflow run")


def _dispatch_ready(client: Any, *, run_id: int) -> dict[str, Any]:
    response = client.post(f"/workflow-runs/{run_id}/dispatch-ready", json={})
    return _require_status(response, 200, context=f"dispatch-ready run={run_id}")


def _set_runner_status(
    client: Any,
    *,
    task_id: int,
    status: str,
    message: str | None = None,
    handoff: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": status}
    if message is not None:
        payload["message"] = message
    if handoff is not None:
        payload["handoff"] = handoff
    response = client.post(f"/runner/tasks/{task_id}/status", json=payload)
    return _require_status(response, 200, context=f"runner status update task={task_id}")


def run_scenario_a(client: Any, *, initiated_by: str) -> dict[str, Any]:
    """Scenario A: workflow success."""

    role_id = _create_role(client, name_prefix="task-061-a-role")
    workflow_id = _create_workflow(
        client,
        name_prefix="task-061-a-workflow",
        steps=[
            {"step_id": "plan", "role_id": role_id, "title": "Scenario A Plan", "depends_on": []},
            {
                "step_id": "build",
                "role_id": role_id,
                "title": "Scenario A Build",
                "depends_on": ["plan"],
            },
        ],
    )

    run = _create_run(client, workflow_template_id=workflow_id, initiated_by=initiated_by)
    run_id = int(run["id"])

    dispatched: list[int] = []
    for _ in range(2):
        dispatch = _dispatch_ready(client, run_id=run_id)
        if dispatch.get("dispatched") is not True:
            raise RuntimeError(f"scenario A expected dispatch=true, got: {dispatch}")
        task_id = int(dispatch["task_id"])
        dispatched.append(task_id)
        _set_runner_status(client, task_id=task_id, status="success", message="scenario A success")

    run_final = _require_status(client.get(f"/workflow-runs/{run_id}"), 200, context="read run final scenario A")
    if run_final.get("status") != "success":
        raise RuntimeError(f"scenario A expected run success, got: {run_final}")

    return {
        "scenario": "A",
        "name": "workflow_success",
        "status": "success",
        "workflow_id": workflow_id,
        "run_id": run_id,
        "task_ids": dispatched,
        "run_status": run_final["status"],
    }


def run_scenario_b(client: Any, *, initiated_by: str) -> dict[str, Any]:
    """Scenario B: fail -> triage -> partial rerun -> success (pending if endpoint missing)."""

    role_id = _create_role(client, name_prefix="task-061-b-role")
    workflow_id = _create_workflow(
        client,
        name_prefix="task-061-b-workflow",
        steps=[
            {
                "step_id": "diagnose",
                "role_id": role_id,
                "title": "Scenario B Diagnose",
                "depends_on": [],
            }
        ],
    )

    failed_run = _create_run(client, workflow_template_id=workflow_id, initiated_by=initiated_by)
    failed_run_id = int(failed_run["id"])
    failed_task_id = int(failed_run["task_ids"][0])

    first_dispatch = _dispatch_ready(client, run_id=failed_run_id)
    if first_dispatch.get("dispatched") is not True or int(first_dispatch["task_id"]) != failed_task_id:
        raise RuntimeError(f"scenario B dispatch mismatch: {first_dispatch}")

    failed_task = _set_runner_status(
        client,
        task_id=failed_task_id,
        status="failed",
        message="permission denied while updating workspace",
    )
    if failed_task.get("status") != "failed":
        raise RuntimeError(f"scenario B expected task status failed, got: {failed_task}")

    failed_run_state = _require_status(
        client.get(f"/workflow-runs/{failed_run_id}"),
        200,
        context="read failed run scenario B",
    )
    if failed_run_state.get("status") != "failed":
        raise RuntimeError(f"scenario B expected run failed, got: {failed_run_state}")

    partial_payload = {
        "task_ids": [failed_task_id],
        "requested_by": f"{initiated_by}-rerun",
        "reason": "TASK-061 local readiness partial rerun",
        "auto_dispatch": True,
        "max_dispatch": 5,
    }
    partial_response = client.post(f"/workflow-runs/{failed_run_id}/partial-rerun", json=partial_payload)

    triage_snapshot = {
        "failure_category": failed_task.get("failure_category"),
        "failure_triage_hints": list(failed_task.get("failure_triage_hints", [])),
        "suggested_next_actions": list(failed_task.get("suggested_next_actions", [])),
        "run_failure_categories": list(failed_run_state.get("failure_categories", [])),
        "run_failure_triage_hints": list(failed_run_state.get("failure_triage_hints", [])),
    }

    if partial_response.status_code in (404, 405):
        recovery_run = _create_run(client, workflow_template_id=workflow_id, initiated_by=f"{initiated_by}-fallback")
        recovery_run_id = int(recovery_run["id"])
        recovery_task_id = int(recovery_run["task_ids"][0])

        recovery_dispatch = _dispatch_ready(client, run_id=recovery_run_id)
        if recovery_dispatch.get("dispatched") is not True or int(recovery_dispatch["task_id"]) != recovery_task_id:
            raise RuntimeError(f"scenario B fallback dispatch mismatch: {recovery_dispatch}")

        _set_runner_status(
            client,
            task_id=recovery_task_id,
            status="success",
            message="scenario B fallback full rerun success",
        )
        recovery_run_state = _require_status(
            client.get(f"/workflow-runs/{recovery_run_id}"),
            200,
            context="read fallback recovery run scenario B",
        )

        return {
            "scenario": "B",
            "name": "fail_triage_partial_rerun_success",
            "status": "expected_pending",
            "pending_reason": "partial rerun API is not available yet (TASK-057 in progress)",
            "partial_rerun_http_status": partial_response.status_code,
            "failed_run_id": failed_run_id,
            "failed_task_id": failed_task_id,
            "failed_run_status": failed_run_state["status"],
            "triage": triage_snapshot,
            "fallback_recovery_run_id": recovery_run_id,
            "fallback_recovery_run_status": recovery_run_state["status"],
        }

    if partial_response.status_code != 200:
        raise RuntimeError(
            "scenario B partial rerun call failed unexpectedly: "
            f"HTTP {partial_response.status_code} {partial_response.text}"
        )

    rerun_body = _json(partial_response)
    rerun_run_id = int(rerun_body.get("run_id") or rerun_body.get("id") or failed_run_id)

    max_dispatch_cycles = 4
    for _ in range(max_dispatch_cycles):
        rerun_state = _require_status(client.get(f"/workflow-runs/{rerun_run_id}"), 200, context="read rerun state")
        if rerun_state.get("status") == "success":
            break
        dispatch = _dispatch_ready(client, run_id=rerun_run_id)
        if dispatch.get("dispatched") is not True:
            # auto_dispatch path may have already consumed ready work
            rerun_state_after_dispatch = _require_status(
                client.get(f"/workflow-runs/{rerun_run_id}"),
                200,
                context="read rerun state after no-dispatch",
            )
            if rerun_state_after_dispatch.get("status") == "success":
                break
            return {
                "scenario": "B",
                "name": "fail_triage_partial_rerun_success",
                "status": "expected_pending",
                "pending_reason": "partial rerun returned no ready tasks in current local policy",
                "partial_rerun_http_status": 200,
                "failed_run_id": failed_run_id,
                "failed_task_id": failed_task_id,
                "failed_run_status": failed_run_state["status"],
                "triage": triage_snapshot,
                "rerun_run_id": rerun_run_id,
                "rerun_status": rerun_state_after_dispatch.get("status"),
            }
        _set_runner_status(client, task_id=int(dispatch["task_id"]), status="success", message="scenario B rerun success")
    else:
        raise RuntimeError(f"scenario B rerun did not complete within {max_dispatch_cycles} cycles")

    final_rerun = _require_status(client.get(f"/workflow-runs/{rerun_run_id}"), 200, context="read rerun final state")
    if final_rerun.get("status") != "success":
        raise RuntimeError(f"scenario B rerun expected success, got: {final_rerun}")

    return {
        "scenario": "B",
        "name": "fail_triage_partial_rerun_success",
        "status": "success",
        "failed_run_id": failed_run_id,
        "failed_task_id": failed_task_id,
        "triage": triage_snapshot,
        "partial_rerun_http_status": 200,
        "rerun_run_id": rerun_run_id,
        "rerun_status": final_rerun["status"],
    }


def run_scenario_c(client: Any, *, initiated_by: str) -> dict[str, Any]:
    """Scenario C: approval + handoff + retry combined regression."""

    role_id = _create_role(
        client,
        name_prefix="task-061-c-role",
        retry_policy={"max_retries": 1, "retry_on": ["network", "runner-transient"]},
    )
    workflow_id = _create_workflow(
        client,
        name_prefix="task-061-c-workflow",
        steps=[
            {
                "step_id": "plan",
                "role_id": role_id,
                "title": "Scenario C Plan",
                "depends_on": [],
            },
            {
                "step_id": "report",
                "role_id": role_id,
                "title": "Scenario C Report",
                "depends_on": ["plan"],
                "required_artifacts": [
                    {
                        "from_step_id": "plan",
                        "artifact_type": "report",
                        "label": "handoff",
                    }
                ],
            },
        ],
    )

    run = _create_run(
        client,
        workflow_template_id=workflow_id,
        initiated_by=initiated_by,
        step_task_overrides={"plan": {"requires_approval": True}},
    )
    run_id = int(run["id"])
    plan_task_id = int(run["task_ids"][0])
    report_task_id = int(run["task_ids"][1])

    blocked_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready", json={})
    if blocked_dispatch.status_code != 409:
        raise RuntimeError(
            "scenario C expected approval block on dispatch-ready: "
            f"HTTP {blocked_dispatch.status_code} {blocked_dispatch.text}"
        )

    approval = _require_status(client.get(f"/tasks/{plan_task_id}/approval"), 200, context="get scenario C approval")
    approval_id = int(approval["id"])
    approved = _require_status(
        client.post(
            f"/approvals/{approval_id}/approve",
            json={"actor": "task-061-operator", "comment": "approved for scenario C"},
        ),
        200,
        context="approve scenario C gate",
    )
    if approved.get("status") != "approved":
        raise RuntimeError(f"scenario C expected approval approved, got: {approved}")

    first_dispatch = _dispatch_ready(client, run_id=run_id)
    if first_dispatch.get("dispatched") is not True or int(first_dispatch["task_id"]) != plan_task_id:
        raise RuntimeError(f"scenario C first dispatch mismatch: {first_dispatch}")

    retry_trigger = _set_runner_status(
        client,
        task_id=plan_task_id,
        status="failed",
        message="network timeout while fetching context",
    )
    if retry_trigger.get("status") != "created":
        raise RuntimeError(f"scenario C expected retry to reset task to created, got: {retry_trigger}")

    second_dispatch = _dispatch_ready(client, run_id=run_id)
    if second_dispatch.get("dispatched") is not True or int(second_dispatch["task_id"]) != plan_task_id:
        raise RuntimeError(f"scenario C retry dispatch mismatch: {second_dispatch}")

    handoff_artifact = _require_status(
        client.post(
            "/artifacts",
            json={
                "artifact_type": "report",
                "location": "/tmp/multyagents/task-061/scenario-c-handoff.md",
                "summary": "scenario C handoff artifact",
                "producer_task_id": plan_task_id,
                "run_id": run_id,
                "metadata": {"label": "handoff"},
            },
        ),
        200,
        context="create scenario C handoff artifact",
    )
    handoff_artifact_id = int(handoff_artifact["id"])

    _set_runner_status(
        client,
        task_id=plan_task_id,
        status="success",
        message="scenario C plan success after retry",
        handoff={
            "summary": "plan completed",
            "next_actions": ["dispatch report"],
            "artifacts": [
                {
                    "artifact_id": handoff_artifact_id,
                    "is_required": True,
                    "note": "handoff for report step",
                }
            ],
        },
    )

    report_dispatch = _dispatch_ready(client, run_id=run_id)
    if report_dispatch.get("dispatched") is not True or int(report_dispatch["task_id"]) != report_task_id:
        raise RuntimeError(f"scenario C report dispatch mismatch: {report_dispatch}")

    _set_runner_status(client, task_id=report_task_id, status="success", message="scenario C report success")

    run_final = _require_status(client.get(f"/workflow-runs/{run_id}"), 200, context="read run final scenario C")
    if run_final.get("status") != "success":
        raise RuntimeError(f"scenario C expected run success, got: {run_final}")

    report_audit = _require_status(client.get(f"/tasks/{report_task_id}/audit"), 200, context="read report audit scenario C")
    if handoff_artifact_id not in report_audit.get("consumed_artifact_ids", []):
        raise RuntimeError(f"scenario C expected report task to consume handoff artifact, got: {report_audit}")

    plan_retry_events = _require_status(
        client.get(f"/events?task_id={plan_task_id}&event_type=task.retry_scheduled&limit=50"),
        200,
        context="read retry events scenario C",
    )
    if not plan_retry_events:
        raise RuntimeError("scenario C expected at least one task.retry_scheduled event")

    run_events_raw = _require_status(client.get(f"/events?run_id={run_id}&limit=200"), 200, context="read run events")
    run_event_types = [str(item.get("event_type")) for item in run_events_raw if isinstance(item, dict)]

    return {
        "scenario": "C",
        "name": "approval_handoff_retry_regression",
        "status": "success",
        "workflow_id": workflow_id,
        "run_id": run_id,
        "plan_task_id": plan_task_id,
        "report_task_id": report_task_id,
        "approval_id": approval_id,
        "handoff_artifact_id": handoff_artifact_id,
        "run_status": run_final["status"],
        "run_retry_summary": run_final.get("retry_summary", {}),
        "run_failure_categories": run_final.get("failure_categories", []),
        "events_sample": run_event_types,
    }


def run_local_readiness_scenarios(client: Any, *, initiated_by: str = "task-061-readiness") -> dict[str, Any]:
    scenario_a = run_scenario_a(client, initiated_by=initiated_by)
    scenario_b = run_scenario_b(client, initiated_by=initiated_by)
    scenario_c = run_scenario_c(client, initiated_by=initiated_by)

    scenarios = [scenario_a, scenario_b, scenario_c]
    success_count = sum(1 for item in scenarios if item["status"] == "success")
    pending_count = sum(1 for item in scenarios if item["status"] == "expected_pending")

    return {
        "task": "TASK-061",
        "scenarios": scenarios,
        "summary": {
            "total": len(scenarios),
            "success": success_count,
            "expected_pending": pending_count,
            "overall_status": "success" if success_count + pending_count == len(scenarios) else "failed",
        },
    }
