from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _mock_runner_submit_success(monkeypatch) -> None:  # noqa: ANN001
    class _SuccessResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _SuccessResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


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


def test_shared_workspace_requires_project_and_lock_paths() -> None:
    role_id = _create_role("shared-validate")
    missing_project = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "shared task no project",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "lock_paths": ["/tmp/multyagents/shared-validate/src"],
        },
    )
    assert missing_project.status_code == 422

    project_id = _create_project(
        name="shared-validate-project",
        root_path="/tmp/multyagents/shared-validate",
        allowed_path="/tmp/multyagents/shared-validate/src",
    )
    missing_locks = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "shared task no locks",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": [],
        },
    )
    assert missing_locks.status_code == 422


def test_shared_workspace_dispatch_conflicts_on_overlapping_paths(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    role_id = _create_role("shared-conflict")
    project_id = _create_project(
        name="shared-conflict-project",
        root_path="/tmp/multyagents/shared-conflict",
        allowed_path="/tmp/multyagents/shared-conflict/src",
    )

    first_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "first shared task",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-conflict/src"],
        },
    )
    assert first_task.status_code == 200

    first_dispatch = client.post(f"/tasks/{first_task.json()['id']}/dispatch")
    assert first_dispatch.status_code == 200
    workspace = first_dispatch.json()["runner_payload"]["workspace"]
    assert workspace["project_id"] == project_id
    assert workspace["lock_paths"] == ["/tmp/multyagents/shared-conflict/src"]

    conflicting_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "second shared task",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-conflict/src/module"],
        },
    )
    assert conflicting_task.status_code == 200

    conflicting_dispatch = client.post(f"/tasks/{conflicting_task.json()['id']}/dispatch")
    assert conflicting_dispatch.status_code == 409
    assert "lock conflict" in conflicting_dispatch.json()["detail"]


def test_release_locks_allows_follow_up_dispatch(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    role_id = _create_role("shared-release")
    project_id = _create_project(
        name="shared-release-project",
        root_path="/tmp/multyagents/shared-release",
        allowed_path="/tmp/multyagents/shared-release/src",
    )

    holder_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "holder",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-release/src"],
        },
    )
    assert holder_task.status_code == 200
    holder_id = holder_task.json()["id"]
    assert client.post(f"/tasks/{holder_id}/dispatch").status_code == 200

    blocked_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "blocked",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-release/src/subdir"],
        },
    )
    assert blocked_task.status_code == 200
    blocked_id = blocked_task.json()["id"]
    assert client.post(f"/tasks/{blocked_id}/dispatch").status_code == 409

    release = client.post(f"/tasks/{holder_id}/locks/release")
    assert release.status_code == 200
    assert release.json()["task_id"] == holder_id
    assert release.json()["released_paths"] == ["/tmp/multyagents/shared-release/src"]

    retry = client.post(f"/tasks/{blocked_id}/dispatch")
    assert retry.status_code == 200


def test_submit_failure_releases_shared_workspace_lock(monkeypatch) -> None:
    monkeypatch.delenv("HOST_RUNNER_URL", raising=False)
    monkeypatch.delenv("API_HOST_RUNNER_URL", raising=False)

    role_id = _create_role("shared-submit-failure")
    project_id = _create_project(
        name="shared-submit-failure-project",
        root_path="/tmp/multyagents/shared-submit-failure",
        allowed_path="/tmp/multyagents/shared-submit-failure/src",
    )

    first_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "first lock",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-submit-failure/src"],
        },
    )
    assert first_task.status_code == 200
    first_dispatch = client.post(f"/tasks/{first_task.json()['id']}/dispatch")
    assert first_dispatch.status_code == 200
    assert first_dispatch.json()["runner_submission"]["submitted"] is False

    second_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "second lock",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-submit-failure/src/module"],
        },
    )
    assert second_task.status_code == 200
    second_dispatch = client.post(f"/tasks/{second_task.json()['id']}/dispatch")
    assert second_dispatch.status_code == 200


def test_shared_workspace_rejects_path_outside_allowed_paths() -> None:
    role_id = _create_role("shared-allowlist")
    project_id = _create_project(
        name="shared-allowlist-project",
        root_path="/tmp/multyagents/shared-allowlist",
        allowed_path="/tmp/multyagents/shared-allowlist/src",
    )

    response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "outside allowlist",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/shared-allowlist/docs"],
        },
    )
    assert response.status_code == 422
    assert "outside allowed paths" in response.json()["detail"]
