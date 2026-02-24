from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_dispatch_requires_explicit_approval_when_gate_enabled() -> None:
    role_id = _create_role("approval-gated")
    task_response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "gated task",
            "context7_mode": "inherit",
            "requires_approval": True,
        },
    )
    assert task_response.status_code == 200
    task = task_response.json()
    assert task["requires_approval"] is True

    approval_response = client.get(f"/tasks/{task['id']}/approval")
    assert approval_response.status_code == 200
    approval = approval_response.json()
    assert approval["status"] == "pending"

    blocked_dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert blocked_dispatch.status_code == 409
    assert "status=pending" in blocked_dispatch.json()["detail"]

    approved = client.post(
        f"/approvals/{approval['id']}/approve",
        json={"actor": "operator", "comment": "approved from test"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    allowed_dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert allowed_dispatch.status_code == 200

    audit = client.get(f"/tasks/{task['id']}/audit")
    assert audit.status_code == 200
    assert audit.json()["requires_approval"] is True
    assert audit.json()["approval_status"] == "approved"


def test_rejected_approval_keeps_dispatch_blocked() -> None:
    role_id = _create_role("approval-rejected")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "rejected task",
            "context7_mode": "inherit",
            "requires_approval": True,
        },
    ).json()

    approval = client.get(f"/tasks/{task['id']}/approval").json()
    rejected = client.post(
        f"/approvals/{approval['id']}/reject",
        json={"actor": "operator", "comment": "rejected from test"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert dispatch.status_code == 409
    assert "status=rejected" in dispatch.json()["detail"]


def test_task_without_approval_gate_has_no_approval_record() -> None:
    role_id = _create_role("approval-optional")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "no gate task",
            "context7_mode": "inherit",
            "requires_approval": False,
        },
    ).json()

    missing = client.get(f"/tasks/{task['id']}/approval")
    assert missing.status_code == 404

    dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert dispatch.status_code == 200
