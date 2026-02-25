from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def test_create_list_get_project_with_valid_paths() -> None:
    created = client.post(
        "/projects",
        json={
            "name": "workspace-main",
            "root_path": "/tmp/multyagents/project",
            "allowed_paths": [
                "/tmp/multyagents/project/src",
                "/tmp/multyagents/project/docs",
            ],
        },
    )
    assert created.status_code == 200
    project = created.json()

    assert project["name"] == "workspace-main"
    assert project["root_path"] == "/tmp/multyagents/project"

    listed = client.get("/projects")
    assert listed.status_code == 200
    project_ids = {item["id"] for item in listed.json()}
    assert project["id"] in project_ids

    fetched = client.get(f"/projects/{project['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == project["id"]


def test_update_and_delete_project() -> None:
    created = client.post(
        "/projects",
        json={
            "name": "project-update-delete",
            "root_path": "/tmp/multyagents/project-upd",
            "allowed_paths": ["/tmp/multyagents/project-upd/src"],
        },
    )
    assert created.status_code == 200
    project_id = created.json()["id"]

    updated = client.put(
        f"/projects/{project_id}",
        json={
            "name": "project-updated",
            "root_path": "/tmp/multyagents/project-upd",
            "allowed_paths": ["/tmp/multyagents/project-upd/src", "/tmp/multyagents/project-upd/docs"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "project-updated"
    assert "/tmp/multyagents/project-upd/docs" in updated.json()["allowed_paths"]

    deleted = client.delete(f"/projects/{project_id}")
    assert deleted.status_code == 204
    missing = client.get(f"/projects/{project_id}")
    assert missing.status_code == 404


def test_delete_project_with_linked_workflow_returns_conflict() -> None:
    role = client.post("/roles", json={"name": "project-conflict-role", "context7_enabled": True}).json()
    project = client.post(
        "/projects",
        json={
            "name": "project-conflict",
            "root_path": "/tmp/multyagents/project-conflict",
            "allowed_paths": ["/tmp/multyagents/project-conflict/src"],
        },
    ).json()

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "flow-conflict",
            "project_id": project["id"],
            "steps": [
                {"step_id": "plan", "role_id": role["id"], "title": "Plan", "depends_on": []},
            ],
        },
    )
    assert workflow.status_code == 200

    delete_response = client.delete(f"/projects/{project['id']}")
    assert delete_response.status_code == 409


def test_create_project_creates_physical_directories() -> None:
    with tempfile.TemporaryDirectory(prefix="multyagents-project-") as temp_root:
        root = Path(temp_root) / "demo-project"
        src = root / "src"
        docs = root / "docs"

        response = client.post(
            "/projects",
            json={
                "name": "physical-create",
                "root_path": str(root),
                "allowed_paths": [str(src), str(docs)],
            },
        )
        assert response.status_code == 200
        assert root.is_dir()
        assert src.is_dir()
        assert docs.is_dir()


def test_create_project_rejects_relative_root_path() -> None:
    response = client.post(
        "/projects",
        json={
            "name": "bad-root",
            "root_path": "relative/path",
            "allowed_paths": [],
        },
    )
    assert response.status_code == 422


def test_create_project_rejects_allowed_path_outside_root() -> None:
    response = client.post(
        "/projects",
        json={
            "name": "bad-allowed",
            "root_path": "/tmp/multyagents/project",
            "allowed_paths": ["/etc"],
        },
    )
    assert response.status_code == 422


def test_create_project_rejects_relative_allowed_path() -> None:
    response = client.post(
        "/projects",
        json={
            "name": "bad-relative-allowed",
            "root_path": "/tmp/multyagents/project",
            "allowed_paths": ["src"],
        },
    )
    assert response.status_code == 422
