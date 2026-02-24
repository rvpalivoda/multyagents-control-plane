from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_dispatch_ready_respects_workflow_dependencies(monkeypatch) -> None:
    submit_calls: list[dict[str, object]] = []

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

    role_id = _create_role("dag-role")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "dag-template",
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Plan", "depends_on": []},
                {"step_id": "build", "role_id": role_id, "title": "Build", "depends_on": ["plan"]},
            ],
        },
    )
    assert workflow.status_code == 200
    workflow_id = workflow.json()["id"]

    run = client.post("/workflow-runs", json={"workflow_template_id": workflow_id, "initiated_by": "test"})
    assert run.status_code == 200
    run_body = run.json()
    assert len(run_body["task_ids"]) == 2
    first_task_id = run_body["task_ids"][0]
    second_task_id = run_body["task_ids"][1]

    first_task = client.get(f"/tasks/{first_task_id}")
    second_task = client.get(f"/tasks/{second_task_id}")
    assert first_task.status_code == 200
    assert second_task.status_code == 200
    assert first_task.json()["title"] == "Plan"
    assert second_task.json()["title"] == "Build"

    dispatch_first = client.post(f"/workflow-runs/{run_body['id']}/dispatch-ready")
    assert dispatch_first.status_code == 200
    assert dispatch_first.json()["dispatched"] is True
    assert dispatch_first.json()["task_id"] == first_task_id
    assert len(submit_calls) == 1

    blocked = client.post(f"/workflow-runs/{run_body['id']}/dispatch-ready")
    assert blocked.status_code == 200
    assert blocked.json()["dispatched"] is False
    assert blocked.json()["reason"] == "dependencies not satisfied"

    mark_success = client.post(f"/runner/tasks/{first_task_id}/status", json={"status": "success"})
    assert mark_success.status_code == 200
    assert mark_success.json()["status"] == "success"

    dispatch_second = client.post(f"/workflow-runs/{run_body['id']}/dispatch-ready")
    assert dispatch_second.status_code == 200
    assert dispatch_second.json()["dispatched"] is True
    assert dispatch_second.json()["task_id"] == second_task_id
    assert len(submit_calls) == 2
