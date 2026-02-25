from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _stub_runner_submit_success(monkeypatch) -> None:  # noqa: ANN001
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if url.endswith("/tasks/submit"):
            return _Response()
        raise AssertionError(f"unexpected runner call: {url}")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_task_quality_gate_policy_summary_includes_blockers_and_warnings(monkeypatch) -> None:
    _stub_runner_submit_success(monkeypatch)
    role_id = _create_role("quality-gates-task-role")

    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "quality gate task",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
            "quality_gate_policy": {
                "required_checks": [
                    {"check": "task-status", "required": True, "severity": "blocker"},
                    {"check": "handoff-present", "required": True, "severity": "warn"},
                ]
            },
        },
    )
    assert created.status_code == 200
    task = created.json()
    task_id = task["id"]
    assert task["quality_gate_policy"]["required_checks"][0]["check"] == "task-status"
    assert task["quality_gate_summary"]["status"] == "pending"
    assert task["quality_gate_summary"]["pending_checks"] == 2

    dispatched = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatched.status_code == 200

    success = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "success", "message": "done"},
    )
    assert success.status_code == 200
    task_body = success.json()
    assert task_body["status"] == "success"
    assert task_body["quality_gate_summary"]["status"] == "pass"
    assert task_body["quality_gate_summary"]["blocker_failures"] == 0
    assert task_body["quality_gate_summary"]["warning_failures"] == 1

    check_by_name = {
        item["check"]: item for item in task_body["quality_gate_summary"]["checks"]
    }
    assert check_by_name["task-status"]["status"] == "pass"
    assert check_by_name["handoff-present"]["status"] == "fail"


def test_workflow_run_quality_gate_summary_aggregates_task_checks(monkeypatch) -> None:
    _stub_runner_submit_success(monkeypatch)
    role_id = _create_role("quality-gates-run-role")

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "quality-gates-run-template",
            "steps": [
                {
                    "step_id": "draft",
                    "role_id": role_id,
                    "title": "Draft",
                    "depends_on": [],
                    "quality_gate_policy": {
                        "required_checks": [
                            {"check": "task-status", "required": True, "severity": "blocker"}
                        ]
                    },
                },
                {
                    "step_id": "finalize",
                    "role_id": role_id,
                    "title": "Finalize",
                    "depends_on": ["draft"],
                    "quality_gate_policy": {
                        "required_checks": [
                            {"check": "task-status", "required": True, "severity": "blocker"},
                            {"check": "handoff-present", "required": True, "severity": "blocker"},
                        ]
                    },
                },
            ],
        },
    )
    assert workflow.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow.json()["id"], "initiated_by": "quality-gates-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    first_task_id = run.json()["task_ids"][0]
    second_task_id = run.json()["task_ids"][1]

    created_run = client.get(f"/workflow-runs/{run_id}")
    assert created_run.status_code == 200
    assert created_run.json()["quality_gate_summary"]["status"] == "pending"

    first_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert first_dispatch.status_code == 200
    assert first_dispatch.json()["task_id"] == first_task_id
    first_success = client.post(f"/runner/tasks/{first_task_id}/status", json={"status": "success"})
    assert first_success.status_code == 200

    second_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert second_dispatch.status_code == 200
    assert second_dispatch.json()["task_id"] == second_task_id
    second_failed = client.post(
        f"/runner/tasks/{second_task_id}/status",
        json={"status": "failed", "message": "tests failed"},
    )
    assert second_failed.status_code == 200

    run_after_failure = client.get(f"/workflow-runs/{run_id}")
    assert run_after_failure.status_code == 200
    run_payload = run_after_failure.json()
    assert run_payload["quality_gate_summary"]["status"] == "fail"
    assert run_payload["quality_gate_summary"]["failing_tasks"] >= 1
    assert run_payload["quality_gate_summary"]["blocker_failures"] >= 1

    execution_summary = client.get(f"/workflow-runs/{run_id}/execution-summary")
    assert execution_summary.status_code == 200
    summary_payload = execution_summary.json()
    assert summary_payload["run"]["quality_gate_summary"]["status"] == "fail"
    task_summary_by_id = {
        item["task_id"]: item["quality_gate_summary"] for item in summary_payload["tasks"]
    }
    assert task_summary_by_id[first_task_id]["status"] == "pass"
    assert task_summary_by_id[second_task_id]["status"] == "fail"
