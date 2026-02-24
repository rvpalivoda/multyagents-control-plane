from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _mock_runner_submit_success(monkeypatch) -> None:  # noqa: ANN001
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_workflow_run_transitions_to_success_when_all_tasks_succeed(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    role_id = _create_role("rollup-success-role")
    task_1 = client.post("/tasks", json={"role_id": role_id, "title": "rollup-1", "context7_mode": "inherit"}).json()
    task_2 = client.post("/tasks", json={"role_id": role_id, "title": "rollup-2", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [task_1["id"], task_2["id"]], "initiated_by": "test"}).json()

    assert client.post(f"/tasks/{task_1['id']}/dispatch").status_code == 200
    assert client.post(f"/tasks/{task_2['id']}/dispatch").status_code == 200
    assert client.post(f"/runner/tasks/{task_1['id']}/status", json={"status": "success"}).status_code == 200
    assert client.post(f"/runner/tasks/{task_2['id']}/status", json={"status": "success"}).status_code == 200

    current_run = client.get(f"/workflow-runs/{run['id']}")
    assert current_run.status_code == 200
    assert current_run.json()["status"] == "success"


def test_workflow_run_transitions_to_failed_on_task_failure(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    role_id = _create_role("rollup-failed-role")
    task = client.post("/tasks", json={"role_id": role_id, "title": "rollup-fail", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [task["id"]], "initiated_by": "test"}).json()

    assert client.post(f"/tasks/{task['id']}/dispatch").status_code == 200
    assert client.post(f"/runner/tasks/{task['id']}/status", json={"status": "failed"}).status_code == 200

    current_run = client.get(f"/workflow-runs/{run['id']}")
    assert current_run.status_code == 200
    assert current_run.json()["status"] == "failed"
