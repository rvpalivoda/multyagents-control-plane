from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _create_project(name: str, root_path: str, allowed_path: str) -> int:
    response = client.post(
        "/projects",
        json={
            "name": name,
            "root_path": root_path,
            "allowed_paths": [allowed_path],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_runner_status_callback_updates_task_and_releases_locks(monkeypatch) -> None:
    class _SuccessResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _SuccessResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("runner-status-role")
    project_id = _create_project(
        name="runner-status-project",
        root_path="/tmp/multyagents/runner-status",
        allowed_path="/tmp/multyagents/runner-status/src",
    )

    holder_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "holder",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/runner-status/src"],
        },
    )
    assert holder_task.status_code == 200
    holder_id = holder_task.json()["id"]

    dispatched = client.post(f"/tasks/{holder_id}/dispatch")
    assert dispatched.status_code == 200
    assert client.get(f"/tasks/{holder_id}").json()["status"] == "queued"

    blocked_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "blocked",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/runner-status/src/module"],
        },
    )
    assert blocked_task.status_code == 200
    blocked_id = blocked_task.json()["id"]
    assert client.post(f"/tasks/{blocked_id}/dispatch").status_code == 409

    running = client.post(f"/runner/tasks/{holder_id}/status", json={"status": "running"})
    assert running.status_code == 200
    assert running.json()["status"] == "running"

    success = client.post(
        f"/runner/tasks/{holder_id}/status",
        json={"status": "success", "message": "done", "exit_code": 0},
    )
    assert success.status_code == 200
    assert success.json()["status"] == "success"
    assert success.json()["exit_code"] == 0

    retry = client.post(f"/tasks/{blocked_id}/dispatch")
    assert retry.status_code == 200


def test_runner_status_callback_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("API_RUNNER_CALLBACK_TOKEN", "secret-token")

    role_id = _create_role("runner-token-role")
    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "token task",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    unauthorized = client.post(f"/runner/tasks/{task_id}/status", json={"status": "running"})
    assert unauthorized.status_code == 401

    authorized = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "running"},
        headers={"X-Runner-Token": "secret-token"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["status"] == "running"


def test_runner_status_callback_updates_isolated_worktree_cleanup_audit(monkeypatch) -> None:
    class _SuccessResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _SuccessResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("runner-isolated-cleanup-role")
    project_id = _create_project(
        name="runner-isolated-cleanup-project",
        root_path="/tmp/multyagents/runner-isolated-cleanup",
        allowed_path="/tmp/multyagents/runner-isolated-cleanup/src",
    )

    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "isolated cleanup task",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project_id,
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    dispatched = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatched.status_code == 200

    success = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "success",
            "message": "isolated done",
            "exit_code": 0,
            "worktree_cleanup_attempted": True,
            "worktree_cleanup_succeeded": True,
            "worktree_cleanup_message": None,
        },
    )
    assert success.status_code == 200
    assert success.json()["status"] == "success"

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    body = audit.json()
    assert body["worktree_cleanup_attempted"] is True
    assert body["worktree_cleanup_succeeded"] is True
    assert body["worktree_cleanup_message"] is None
    assert body["worktree_cleanup_at"] is not None

    released = client.get(f"/events?task_id={task_id}&event_type=task.worktree_session_released&limit=20")
    assert released.status_code == 200
    assert any(item["payload"].get("reason") == "runner-status-success" for item in released.json())
