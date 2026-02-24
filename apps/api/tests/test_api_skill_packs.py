from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def test_skill_pack_crud_and_usage() -> None:
    created = client.post(
        "/skill-packs",
        json={
            "name": "platform-core",
            "skills": ["skills/task-governance", "skills/api-orchestrator-fastapi"],
        },
    )
    assert created.status_code == 200
    pack = created.json()
    assert pack["name"] == "platform-core"
    assert pack["skills"] == ["skills/task-governance", "skills/api-orchestrator-fastapi"]
    assert pack["used_by_role_ids"] == []

    role = client.post(
        "/roles",
        json={
            "name": "pack-user",
            "context7_enabled": True,
            "skill_packs": ["platform-core"],
        },
    )
    assert role.status_code == 200
    role_id = role.json()["id"]

    fetched = client.get(f"/skill-packs/{pack['id']}")
    assert fetched.status_code == 200
    assert role_id in fetched.json()["used_by_role_ids"]

    updated = client.put(
        f"/skill-packs/{pack['id']}",
        json={
            "name": "platform-core-v2",
            "skills": ["skills/task-governance"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "platform-core-v2"

    old_role_update = client.put(
        f"/roles/{role_id}",
        json={
            "name": "pack-user",
            "context7_enabled": True,
            "system_prompt": "",
            "allowed_tools": [],
            "skill_packs": ["platform-core"],
            "execution_constraints": {},
        },
    )
    assert old_role_update.status_code == 422

    new_role_update = client.put(
        f"/roles/{role_id}",
        json={
            "name": "pack-user",
            "context7_enabled": True,
            "system_prompt": "",
            "allowed_tools": [],
            "skill_packs": ["platform-core-v2"],
            "execution_constraints": {},
        },
    )
    assert new_role_update.status_code == 200

    delete_conflict = client.delete(f"/skill-packs/{pack['id']}")
    assert delete_conflict.status_code == 409

    role_cleanup = client.delete(f"/roles/{role_id}")
    assert role_cleanup.status_code == 204

    delete_ok = client.delete(f"/skill-packs/{pack['id']}")
    assert delete_ok.status_code == 204


def test_skill_pack_validates_catalog_and_uniqueness() -> None:
    unknown_skill = client.post(
        "/skill-packs",
        json={"name": "invalid-pack", "skills": ["skills/not-in-catalog"]},
    )
    assert unknown_skill.status_code == 422

    first = client.post(
        "/skill-packs",
        json={"name": "unique-pack", "skills": ["skills/task-governance"]},
    )
    assert first.status_code == 200

    duplicate = client.post(
        "/skill-packs",
        json={"name": "unique-pack", "skills": ["skills/task-governance"]},
    )
    assert duplicate.status_code == 409


def test_role_rejects_unknown_skill_pack_name() -> None:
    response = client.post(
        "/roles",
        json={
            "name": "unknown-pack-role",
            "context7_enabled": True,
            "skill_packs": ["pack-that-does-not-exist"],
        },
    )
    assert response.status_code == 422
