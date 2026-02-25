from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _mock_runner_submit_success(monkeypatch, submit_calls: list[dict[str, object]]) -> None:  # noqa: ANN001
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if url.endswith("/tasks/submit"):
            submit_calls.append(kwargs["json"])
            return _Response()
        raise AssertionError(f"unexpected runner call: {url}")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_assistant_plan_intent_returns_machine_readable_plan() -> None:
    role_id = _create_role("assistant-plan-role")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "assistant-plan-template",
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Plan", "depends_on": []},
                {"step_id": "report", "role_id": role_id, "title": "Report", "depends_on": ["plan"]},
            ],
        },
    )
    assert workflow.status_code == 200
    workflow_id = workflow.json()["id"]

    response = client.post(
        "/assistant/intents/plan",
        json={
            "workflow_template_id": workflow_id,
            "initiated_by": "assistant-test",
            "step_task_overrides": {
                "plan": {"requires_approval": True},
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_template_id"] == workflow_id
    assert body["machine_summary"]["phase"] == "plan"
    assert body["machine_summary"]["total_tasks"] == 2
    assert body["machine_summary"]["planned_step_ids"] == ["plan", "report"]
    assert body["machine_summary"]["planned_approval_step_ids"] == ["plan"]
    assert body["steps"][0]["task_config"]["requires_approval"] is True


def test_assistant_start_dispatches_ready_tasks_and_reports_approval_blocks(monkeypatch) -> None:
    submit_calls: list[dict[str, object]] = []
    _mock_runner_submit_success(monkeypatch, submit_calls)

    role_id = _create_role("assistant-start-role")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "assistant-start-template",
            "steps": [
                {"step_id": "gated", "role_id": role_id, "title": "Gated", "depends_on": []},
                {"step_id": "free", "role_id": role_id, "title": "Free", "depends_on": []},
            ],
        },
    )
    assert workflow.status_code == 200

    started = client.post(
        "/assistant/intents/start",
        json={
            "workflow_template_id": workflow.json()["id"],
            "initiated_by": "assistant-start",
            "dispatch_ready": True,
            "step_task_overrides": {"gated": {"requires_approval": True}},
        },
    )
    assert started.status_code == 200
    body = started.json()
    assert len(body["dispatches"]) == 1
    assert len(body["blocked_by_approval_task_ids"]) == 1
    assert body["machine_summary"]["workflow_status"] == "running"
    assert len(body["machine_summary"]["ready_task_ids"]) == 0
    assert body["machine_summary"]["blocked_by_approval_task_ids"] == body["blocked_by_approval_task_ids"]
    assert len(submit_calls) == 1

    blocked_task_id = body["blocked_by_approval_task_ids"][0]
    approval = client.get(f"/tasks/{blocked_task_id}/approval")
    assert approval.status_code == 200
    assert approval.json()["status"] == "pending"


def test_assistant_status_and_report_include_machine_summary(monkeypatch) -> None:
    submit_calls: list[dict[str, object]] = []
    _mock_runner_submit_success(monkeypatch, submit_calls)

    role_id = _create_role("assistant-report-role")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "assistant-report-template",
            "steps": [{"step_id": "single", "role_id": role_id, "title": "Single", "depends_on": []}],
        },
    )
    assert workflow.status_code == 200

    started = client.post(
        "/assistant/intents/start",
        json={
            "workflow_template_id": workflow.json()["id"],
            "initiated_by": "assistant-report",
            "dispatch_ready": True,
        },
    )
    assert started.status_code == 200
    run_id = started.json()["run"]["id"]
    task_id = started.json()["run"]["task_ids"][0]

    artifact = client.post(
        "/artifacts",
        json={
            "artifact_type": "report",
            "location": "/tmp/multyagents/assistant/report.md",
            "summary": "assistant report artifact",
            "producer_task_id": task_id,
            "run_id": run_id,
            "metadata": {"label": "assistant-summary"},
        },
    )
    assert artifact.status_code == 200
    artifact_id = artifact.json()["id"]

    status_update = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "success",
            "handoff": {
                "summary": "task complete",
                "next_actions": ["publish report"],
                "artifacts": [{"artifact_id": artifact_id, "is_required": True}],
            },
        },
    )
    assert status_update.status_code == 200

    status = client.post("/assistant/intents/status", json={"run_id": run_id})
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["machine_summary"]["workflow_status"] == "success"
    assert status_body["machine_summary"]["task_status_counts"]["success"] == 1
    assert artifact_id in status_body["machine_summary"]["produced_artifact_ids"]
    assert task_id in status_body["machine_summary"]["handoff_task_ids"]
    assert status_body["machine_summary"]["failed_task_ids"] == []

    report = client.post(
        "/assistant/intents/report",
        json={"run_id": run_id, "event_limit": 100, "artifact_limit": 100, "handoff_limit": 100},
    )
    assert report.status_code == 200
    report_body = report.json()
    assert any(item["id"] == artifact_id for item in report_body["artifacts"])
    assert any(item["event_type"] == "task.handoff_published" for item in report_body["events"])
    assert report_body["machine_summary"]["workflow_status"] == "success"
    assert "task.runner_status_updated" in report_body["machine_summary"]["recent_event_types"]


def test_assistant_intents_validate_overrides_and_run_ids() -> None:
    role_id = _create_role("assistant-invalid-role")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "assistant-invalid-template",
            "steps": [{"step_id": "a", "role_id": role_id, "title": "A", "depends_on": []}],
        },
    )
    assert workflow.status_code == 200

    bad_override = client.post(
        "/assistant/intents/plan",
        json={
            "workflow_template_id": workflow.json()["id"],
            "step_task_overrides": {"missing": {"requires_approval": True}},
        },
    )
    assert bad_override.status_code == 422
    assert "unknown workflow step overrides" in bad_override.json()["detail"]

    missing_status = client.post("/assistant/intents/status", json={"run_id": 999999})
    assert missing_status.status_code == 404

    missing_report = client.post("/assistant/intents/report", json={"run_id": 999999})
    assert missing_report.status_code == 404
