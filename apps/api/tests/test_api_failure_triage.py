from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _stub_runner(monkeypatch) -> None:
    class _SuccessResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _SuccessResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_failed_task_gets_failure_triage_fields(monkeypatch) -> None:
    _stub_runner(monkeypatch)
    role_id = _create_role("triage-task-role")

    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "triage task",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    dispatched = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatched.status_code == 200

    failed = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "failed", "message": "connection refused", "exit_code": 1},
    )
    assert failed.status_code == 200
    body = failed.json()
    assert body["status"] == "failed"
    assert body["failure_category"] == "network"
    assert len(body["failure_triage_hints"]) > 0
    assert len(body["suggested_next_actions"]) > 0


def test_failed_workflow_run_exposes_run_level_triage(monkeypatch) -> None:
    _stub_runner(monkeypatch)
    role_id = _create_role("triage-run-role")

    template = client.post(
        "/workflow-templates",
        json={
            "name": "triage-run-template",
            "steps": [
                {
                    "step_id": "analyze",
                    "role_id": role_id,
                    "title": "Analyze",
                    "depends_on": [],
                }
            ],
        },
    )
    assert template.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": template.json()["id"], "initiated_by": "test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    task_id = run.json()["task_ids"][0]

    dispatched = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatched.status_code == 200

    failed = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "failed", "message": "permission denied", "exit_code": 1},
    )
    assert failed.status_code == 200

    run_read = client.get(f"/workflow-runs/{run_id}")
    assert run_read.status_code == 200
    payload = run_read.json()
    assert "permission" in payload["failure_categories"]
    assert len(payload["failure_triage_hints"]) > 0
    assert len(payload["suggested_next_actions"]) > 0
