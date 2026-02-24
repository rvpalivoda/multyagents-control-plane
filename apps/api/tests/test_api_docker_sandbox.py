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


def test_docker_sandbox_requires_project_and_sandbox() -> None:
    role_id = _create_role("docker-requires")

    missing_project = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "docker without project",
            "execution_mode": "docker-sandbox",
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo ok"],
            },
        },
    )
    assert missing_project.status_code == 422

    project_id = _create_project(
        name="docker-requires-project",
        root_path="/tmp/multyagents/docker-requires",
        allowed_path="/tmp/multyagents/docker-requires/src",
    )
    missing_sandbox = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "docker without sandbox",
            "execution_mode": "docker-sandbox",
            "project_id": project_id,
        },
    )
    assert missing_sandbox.status_code == 422


def test_docker_sandbox_dispatch_builds_payload_and_audit(monkeypatch) -> None:  # noqa: ANN001
    captured_payload: dict[str, object] = {}

    class _SuccessResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal captured_payload
        captured_payload = kwargs["json"]
        return _SuccessResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("docker-dispatch")
    project_id = _create_project(
        name="docker-dispatch-project",
        root_path="/tmp/multyagents/docker-dispatch",
        allowed_path="/tmp/multyagents/docker-dispatch/src",
    )

    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "run in docker",
            "execution_mode": "docker-sandbox",
            "project_id": project_id,
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo docker ok"],
                "workdir": "/workspace/project",
                "env": {"A": "B"},
            },
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200
    body = dispatch.json()
    sandbox = body["runner_payload"]["sandbox"]
    assert sandbox["image"] == "alpine:3.20"
    assert sandbox["command"] == ["sh", "-lc", "echo docker ok"]
    assert sandbox["workdir"] == "/workspace/project"
    assert sandbox["env"] == {"A": "B"}
    assert sandbox["mounts"] == [
        {
            "source": "/tmp/multyagents/docker-dispatch/src",
            "target": "/workspace/project",
            "read_only": False,
        }
    ]
    assert captured_payload["sandbox"]["image"] == "alpine:3.20"
    assert captured_payload["sandbox"]["mounts"][0]["source"] == "/tmp/multyagents/docker-dispatch/src"

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert audit.json()["sandbox_image"] == "alpine:3.20"
    assert audit.json()["sandbox_workdir"] == "/workspace/project"


def test_docker_sandbox_runner_status_updates_audit() -> None:
    role_id = _create_role("docker-status")
    project_id = _create_project(
        name="docker-status-project",
        root_path="/tmp/multyagents/docker-status",
        allowed_path="/tmp/multyagents/docker-status/src",
    )
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "status update",
            "execution_mode": "docker-sandbox",
            "project_id": project_id,
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "exit 1"],
                "workdir": "/workspace/project",
                "mounts": [
                    {
                        "source": "/tmp/multyagents/docker-status/src",
                        "target": "/workspace/project",
                        "read_only": True,
                    }
                ],
            },
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]
    assert client.post(f"/tasks/{task_id}/dispatch").status_code == 200

    update = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "failed",
            "message": "docker run failed",
            "exit_code": 125,
            "container_id": "multyagents-task-1",
        },
    )
    assert update.status_code == 200

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert audit.json()["sandbox_container_id"] == "multyagents-task-1"
    assert audit.json()["sandbox_exit_code"] == 125
    assert audit.json()["sandbox_error"] == "docker run failed"
