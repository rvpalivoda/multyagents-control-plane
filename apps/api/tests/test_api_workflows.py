from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_project() -> int:
    response = client.post(
        "/projects",
        json={
            "name": "workflow-project",
            "root_path": "/tmp/multyagents/workflows",
            "allowed_paths": ["/tmp/multyagents/workflows/src"],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_workflow_template_crud() -> None:
    role_id = _create_role("workflow-coder")
    project_id = _create_project()

    create = client.post(
        "/workflow-templates",
        json={
            "name": "feature-flow",
            "project_id": project_id,
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Plan", "depends_on": []},
                {"step_id": "build", "role_id": role_id, "title": "Build", "depends_on": ["plan"]},
            ],
        },
    )
    assert create.status_code == 200
    workflow = create.json()

    listed = client.get("/workflow-templates")
    assert listed.status_code == 200
    workflow_ids = {item["id"] for item in listed.json()}
    assert workflow["id"] in workflow_ids

    fetched = client.get(f"/workflow-templates/{workflow['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "feature-flow"

    update = client.put(
        f"/workflow-templates/{workflow['id']}",
        json={
            "name": "feature-flow-v2",
            "project_id": project_id,
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Plan", "depends_on": []},
                {"step_id": "review", "role_id": role_id, "title": "Review", "depends_on": ["plan"]},
            ],
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "feature-flow-v2"

    deleted = client.delete(f"/workflow-templates/{workflow['id']}")
    assert deleted.status_code == 204

    get_after_delete = client.get(f"/workflow-templates/{workflow['id']}")
    assert get_after_delete.status_code == 404


def test_workflow_template_rejects_unknown_dependency() -> None:
    role_id = _create_role("workflow-dep")
    response = client.post(
        "/workflow-templates",
        json={
            "name": "bad-dep-flow",
            "steps": [
                {"step_id": "a", "role_id": role_id, "title": "A", "depends_on": ["missing"]}
            ],
        },
    )
    assert response.status_code == 422


def test_workflow_template_rejects_cycle() -> None:
    role_id = _create_role("workflow-cycle")
    response = client.post(
        "/workflow-templates",
        json={
            "name": "bad-cycle-flow",
            "steps": [
                {"step_id": "a", "role_id": role_id, "title": "A", "depends_on": ["b"]},
                {"step_id": "b", "role_id": role_id, "title": "B", "depends_on": ["a"]},
            ],
        },
    )
    assert response.status_code == 422


def test_workflow_template_requires_existing_role() -> None:
    response = client.post(
        "/workflow-templates",
        json={
            "name": "missing-role-flow",
            "steps": [
                {"step_id": "a", "role_id": 999999, "title": "A", "depends_on": []}
            ],
        },
    )
    assert response.status_code == 404


def test_workflow_template_rejects_artifact_requirement_outside_dependencies() -> None:
    role_id = _create_role("workflow-artifact-dep")
    response = client.post(
        "/workflow-templates",
        json={
            "name": "bad-handoff-flow",
            "steps": [
                {"step_id": "a", "role_id": role_id, "title": "A", "depends_on": []},
                {
                    "step_id": "b",
                    "role_id": role_id,
                    "title": "B",
                    "depends_on": ["a"],
                    "required_artifacts": [
                        {"from_step_id": "missing", "artifact_type": "report", "label": "handoff"}
                    ],
                },
            ],
        },
    )
    assert response.status_code == 422
