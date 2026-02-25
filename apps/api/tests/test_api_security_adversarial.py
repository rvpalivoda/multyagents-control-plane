from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)

_LEAK_TOKEN = "super-secret-token"
_LEAK_API_KEY = "api-key-123"
_LEAK_PASSWORD = "hunter2"


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _create_project(name: str, *, root_path: Path, allowed_paths: list[Path]) -> int:
    response = client.post(
        "/projects",
        json={
            "name": name,
            "root_path": str(root_path),
            "allowed_paths": [str(path) for path in allowed_paths],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _assert_no_secret_leak(value: str) -> None:
    assert _LEAK_TOKEN not in value
    assert _LEAK_API_KEY not in value
    assert _LEAK_PASSWORD not in value


def test_shared_workspace_rejects_path_traversal_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    allowed = root / "src"
    allowed.mkdir(parents=True)

    role_id = _create_role("security-traversal-role")
    project_id = _create_project(
        "security-traversal-project",
        root_path=root,
        allowed_paths=[allowed],
    )

    traversal_path = allowed / ".." / ".." / "escape"
    response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "traversal escape attempt",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": [str(traversal_path)],
        },
    )
    assert response.status_code == 422
    assert "outside project root" in response.json()["detail"]


def test_shared_workspace_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    allowed = root / "src"
    outside = tmp_path / "outside"
    allowed.mkdir(parents=True)
    outside.mkdir()

    symlink_escape = allowed / "escape-link"
    try:
        symlink_escape.symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # pragma: no cover
        pytest.skip(f"symlink creation unavailable in this environment: {exc}")

    role_id = _create_role("security-symlink-role")
    project_id = _create_project(
        "security-symlink-project",
        root_path=root,
        allowed_paths=[allowed],
    )

    response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "symlink escape attempt",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": [str(symlink_escape)],
        },
    )
    assert response.status_code == 422
    assert "outside project root" in response.json()["detail"]


def test_docker_sandbox_rejects_mount_traversal_outside_allowed_paths(tmp_path: Path) -> None:
    root = tmp_path / "project"
    allowed = root / "src"
    allowed.mkdir(parents=True)

    role_id = _create_role("security-docker-traversal-role")
    project_id = _create_project(
        "security-docker-traversal-project",
        root_path=root,
        allowed_paths=[allowed],
    )

    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "docker traversal mount attempt",
            "context7_mode": "inherit",
            "execution_mode": "docker-sandbox",
            "project_id": project_id,
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo denied"],
                "workdir": "/workspace/project",
                "mounts": [
                    {
                        "source": str(allowed / ".." / "secrets"),
                        "target": "/workspace/project",
                        "read_only": False,
                    }
                ],
            },
        },
    )
    assert task.status_code == 200

    dispatch = client.post(f"/tasks/{task.json()['id']}/dispatch")
    assert dispatch.status_code == 422
    assert "outside allowed paths" in dispatch.json()["detail"]


def test_docker_sandbox_rejects_symlink_mount_escape(tmp_path: Path) -> None:
    root = tmp_path / "project"
    allowed = root / "src"
    outside = tmp_path / "outside"
    allowed.mkdir(parents=True)
    outside.mkdir()

    symlink_escape = allowed / "escape-link"
    try:
        symlink_escape.symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # pragma: no cover
        pytest.skip(f"symlink creation unavailable in this environment: {exc}")

    role_id = _create_role("security-docker-symlink-role")
    project_id = _create_project(
        "security-docker-symlink-project",
        root_path=root,
        allowed_paths=[allowed],
    )

    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "docker symlink mount attempt",
            "context7_mode": "inherit",
            "execution_mode": "docker-sandbox",
            "project_id": project_id,
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo denied"],
                "workdir": "/workspace/project",
                "mounts": [
                    {
                        "source": str(symlink_escape),
                        "target": "/workspace/project",
                        "read_only": False,
                    }
                ],
            },
        },
    )
    assert task.status_code == 200

    dispatch = client.post(f"/tasks/{task.json()['id']}/dispatch")
    assert dispatch.status_code == 422
    assert "outside project root" in dispatch.json()["detail"]


def test_task_create_rejects_sandbox_policy_bypass_for_no_workspace() -> None:
    role_id = _create_role("security-policy-bypass-role")

    response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "sandbox policy bypass attempt",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo denied"],
            },
        },
    )
    assert response.status_code == 422
    assert "sandbox is supported only for docker-sandbox mode" in response.text


def test_runner_submit_failure_redacts_secret_values(monkeypatch) -> None:
    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError(
            f"permission denied token={_LEAK_TOKEN} api_key={_LEAK_API_KEY} password={_LEAK_PASSWORD}"
        )

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.invalid")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("security-submit-secret-role")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "submit secret leak check",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200
    submission_message = dispatch.json()["runner_submission"]["message"]
    _assert_no_secret_leak(submission_message)
    assert "[REDACTED]" in submission_message

    task_read = client.get(f"/tasks/{task_id}")
    assert task_read.status_code == 200
    body = task_read.json()
    _assert_no_secret_leak(body["runner_message"])
    assert all(_LEAK_TOKEN not in hint and _LEAK_API_KEY not in hint for hint in body["failure_triage_hints"])

    events = client.get(f"/events?task_id={task_id}&event_type=task.runner_submit_failed&limit=20")
    assert events.status_code == 200
    event_message = events.json()[-1]["payload"]["message"]
    _assert_no_secret_leak(event_message)
    assert "[REDACTED]" in event_message


def test_runner_status_failure_redacts_secret_values() -> None:
    role_id = _create_role("security-status-secret-role")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "status secret leak check",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    failed = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "failed",
            "message": f"permission denied token={_LEAK_TOKEN} password={_LEAK_PASSWORD}",
            "stdout": f"api_key={_LEAK_API_KEY}",
            "stderr": f"token={_LEAK_TOKEN}",
        },
    )
    assert failed.status_code == 200
    body = failed.json()
    _assert_no_secret_leak(body["runner_message"])
    assert "[REDACTED]" in body["runner_message"]

    read_task = client.get(f"/tasks/{task_id}")
    assert read_task.status_code == 200
    _assert_no_secret_leak(read_task.json()["runner_message"])
    assert all(_LEAK_TOKEN not in hint and _LEAK_PASSWORD not in hint for hint in read_task.json()["failure_triage_hints"])

    events = client.get(f"/events?task_id={task_id}&event_type=task.runner_status_updated&limit=20")
    assert events.status_code == 200
    event_message = events.json()[-1]["payload"]["message"]
    _assert_no_secret_leak(event_message)
    assert "[REDACTED]" in event_message
