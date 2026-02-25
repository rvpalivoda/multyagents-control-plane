from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _create_task(role_id: int, title: str) -> int:
    response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": title,
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_cancel_task_endpoint_calls_runner_and_updates_status(monkeypatch) -> None:
    calls: list[str] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "canceled"}

    def fake_post(url, **kwargs):  # noqa: ANN001, ARG001
        calls.append(url)
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("cancel-task-role")
    task_id = _create_task(role_id, "cancel me")

    canceled = client.post(f"/tasks/{task_id}/cancel")
    assert canceled.status_code == 200
    body = canceled.json()
    assert body["status"] == "canceled"
    assert body["runner_message"] == "cancel requested"
    assert calls == [f"http://runner.test/tasks/{task_id}/cancel"]


def test_abort_workflow_run_propagates_cancel_to_all_run_tasks(monkeypatch) -> None:
    calls: list[str] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "canceled"}

    def fake_post(url, **kwargs):  # noqa: ANN001, ARG001
        calls.append(url)
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("abort-run-role")
    task_id_1 = _create_task(role_id, "run task 1")
    task_id_2 = _create_task(role_id, "run task 2")

    run = client.post("/workflow-runs", json={"task_ids": [task_id_1, task_id_2], "initiated_by": "test"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    aborted = client.post(f"/workflow-runs/{run_id}/abort")
    assert aborted.status_code == 200
    assert aborted.json()["status"] == "aborted"

    assert set(calls) == {
        f"http://runner.test/tasks/{task_id_1}/cancel",
        f"http://runner.test/tasks/{task_id_2}/cancel",
    }

    task_1 = client.get(f"/tasks/{task_id_1}")
    task_2 = client.get(f"/tasks/{task_id_2}")
    assert task_1.status_code == 200
    assert task_2.status_code == 200
    assert task_1.json()["status"] == "canceled"
    assert task_2.json()["status"] == "canceled"


def test_cancel_releases_isolated_worktree_session(monkeypatch) -> None:
    calls: list[str] = []

    class _Response:
        def __init__(self, status: str) -> None:
            self._status = status

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": self._status}

    def fake_post(url, **kwargs):  # noqa: ANN001, ARG001
        calls.append(url)
        if url.endswith("/tasks/submit"):
            return _Response("queued")
        if url.endswith("/cancel"):
            return _Response("canceled")
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("cancel-isolated-role")
    project = client.post(
        "/projects",
        json={
            "name": "cancel-isolated-project",
            "root_path": "/tmp/multyagents/cancel-isolated",
            "allowed_paths": ["/tmp/multyagents/cancel-isolated/src"],
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "cancel isolated",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project_id,
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200

    canceled = client.post(f"/tasks/{task_id}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"

    release_events = client.get(f"/events?task_id={task_id}&event_type=task.worktree_session_released&limit=20")
    assert release_events.status_code == 200
    assert any(event["payload"].get("reason") == "cancel-requested" for event in release_events.json())
