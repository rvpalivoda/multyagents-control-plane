from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def test_role_list_update_and_delete() -> None:
    created = client.post(
        "/roles",
        json={
            "name": "planner",
            "context7_enabled": True,
            "system_prompt": "You are a planner",
            "allowed_tools": ["read", "write", "read"],
            "skill_packs": ["core", "planning", "core"],
            "execution_constraints": {"max_steps": 20, "allow_network": True},
        },
    )
    assert created.status_code == 200
    role = created.json()
    assert role["system_prompt"] == "You are a planner"
    assert role["allowed_tools"] == ["read", "write"]
    assert role["skill_packs"] == ["core", "planning"]
    assert role["execution_constraints"]["max_steps"] == 20

    listed = client.get("/roles")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert role["id"] in ids

    updated = client.put(
        f"/roles/{role['id']}",
        json={
            "name": "planner-updated",
            "context7_enabled": False,
            "system_prompt": "Updated prompt",
            "allowed_tools": ["terminal", "git"],
            "skill_packs": ["delivery"],
            "execution_constraints": {"max_runtime_seconds": 300},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "planner-updated"
    assert updated.json()["context7_enabled"] is False
    assert updated.json()["system_prompt"] == "Updated prompt"
    assert updated.json()["allowed_tools"] == ["terminal", "git"]
    assert updated.json()["skill_packs"] == ["delivery"]
    assert updated.json()["execution_constraints"]["max_runtime_seconds"] == 300

    deleted = client.delete(f"/roles/{role['id']}")
    assert deleted.status_code == 204

    get_after_delete = client.get(f"/roles/{role['id']}")
    assert get_after_delete.status_code == 404


def test_delete_role_with_linked_task_returns_conflict() -> None:
    role = client.post("/roles", json={"name": "coder", "context7_enabled": True}).json()
    task = client.post(
        "/tasks",
        json={"role_id": role["id"], "title": "linked", "context7_mode": "inherit"},
    )
    assert task.status_code == 200

    delete_response = client.delete(f"/roles/{role['id']}")
    assert delete_response.status_code == 409
