from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def test_runner_submit_failure_sets_submit_failed_and_triage(monkeypatch) -> None:
    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("runner unreachable")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.invalid")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "inject-submit-fail-role", "context7_enabled": True})
    assert role.status_code == 200

    task = client.post(
        "/tasks",
        json={
            "role_id": role.json()["id"],
            "title": "submit failure task",
            "execution_mode": "no-workspace",
            "context7_mode": "inherit",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200

    read_task = client.get(f"/tasks/{task_id}")
    assert read_task.status_code == 200
    payload = read_task.json()
    assert payload["status"] in {"submit-failed", "failed"}
    assert isinstance(payload.get("failure_triage_hints", []), list)


def test_permission_denied_failure_category_and_next_actions(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "inject-permission-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "inject-permission-flow",
            "steps": [{"step_id": "step", "role_id": role_id, "title": "Step", "depends_on": []}],
        },
    )
    assert workflow.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow.json()["id"], "initiated_by": "inject"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    task_id = run.json()["task_ids"][0]

    dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready", json={})
    assert dispatch.status_code == 200
    assert dispatch.json()["dispatched"] is True

    failed = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "failed", "message": "permission denied while writing file", "exit_code": 1},
    )
    assert failed.status_code == 200

    run_read = client.get(f"/workflow-runs/{run_id}")
    assert run_read.status_code == 200
    body = run_read.json()
    assert "permission" in body.get("failure_categories", []) or body.get("failure_categories")
    assert isinstance(body.get("failure_triage_hints", []), list)
    assert isinstance(body.get("suggested_next_actions", []), list)
