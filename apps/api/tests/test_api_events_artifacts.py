from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_create_and_filter_events() -> None:
    role_id = _create_role("events-role")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "events task",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post("/workflow-runs", json={"task_ids": [task_id], "initiated_by": "test"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200

    created = client.post(
        "/events",
        json={
            "event_type": "agent.note",
            "run_id": run_id,
            "task_id": task_id,
            "producer_role": "writer",
            "payload": {"note": "draft ready"},
        },
    )
    assert created.status_code == 200
    event_id = created.json()["id"]
    assert created.json()["producer_role"] == "writer"

    filtered = client.get(f"/events?task_id={task_id}&event_type=agent.note&limit=100")
    assert filtered.status_code == 200
    filtered_ids = {item["id"] for item in filtered.json()}
    assert event_id in filtered_ids

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert event_id in audit.json()["recent_event_ids"]


def test_create_and_filter_artifacts() -> None:
    role_id = _create_role("artifacts-role")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "artifact task",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post("/workflow-runs", json={"task_ids": [task_id], "initiated_by": "test"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    assert client.post(f"/tasks/{task_id}/dispatch").status_code == 200

    created = client.post(
        "/artifacts",
        json={
            "artifact_type": "text",
            "location": "/tmp/multyagents/artifacts/report.md",
            "summary": "generated report",
            "producer_task_id": task_id,
            "run_id": run_id,
            "metadata": {"lang": "ru"},
        },
    )
    assert created.status_code == 200
    artifact_id = created.json()["id"]
    assert created.json()["task_id"] == task_id
    assert created.json()["artifact_type"] == "text"

    filtered = client.get(f"/artifacts?run_id={run_id}&artifact_type=text&limit=100")
    assert filtered.status_code == 200
    assert artifact_id in {item["id"] for item in filtered.json()}

    artifact_event = client.get(f"/events?task_id={task_id}&event_type=artifact.created&limit=100")
    assert artifact_event.status_code == 200
    assert any(item["payload"].get("artifact_id") == artifact_id for item in artifact_event.json())

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert artifact_id in audit.json()["produced_artifact_ids"]


def test_event_and_artifact_validate_references() -> None:
    bad_event = client.post(
        "/events",
        json={
            "event_type": "agent.note",
            "task_id": 999999,
            "producer_role": "ghost",
            "payload": {},
        },
    )
    assert bad_event.status_code == 404

    bad_artifact = client.post(
        "/artifacts",
        json={
            "artifact_type": "report",
            "location": "/tmp/multyagents/artifacts/bad.txt",
            "summary": "bad ref",
            "producer_task_id": 999999,
        },
    )
    assert bad_artifact.status_code == 404


def test_event_and_artifact_reject_unsupported_contract_version() -> None:
    bad_event_version = client.post(
        "/events",
        json={
            "contract_version": "v2",
            "event_type": "agent.note",
            "task_id": 1,
            "producer_role": "ghost",
            "payload": {},
        },
    )
    assert bad_event_version.status_code == 422

    bad_artifact_version = client.post(
        "/artifacts",
        json={
            "contract_version": "v2",
            "artifact_type": "report",
            "location": "/tmp/multyagents/artifacts/bad-version.txt",
            "summary": "bad version",
            "producer_task_id": 1,
        },
    )
    assert bad_artifact_version.status_code == 422


def test_task_completion_handoff_is_persisted_and_visible_in_timeline() -> None:
    role_id = _create_role("handoff-events-role")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "handoff source task",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post("/workflow-runs", json={"task_ids": [task_id], "initiated_by": "handoff-events"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    assert client.post(f"/tasks/{task_id}/dispatch").status_code == 200

    artifact = client.post(
        "/artifacts",
        json={
            "artifact_type": "report",
            "location": "/tmp/multyagents/handoff/events-report.md",
            "summary": "handoff report",
            "producer_task_id": task_id,
            "run_id": run_id,
            "metadata": {"label": "handoff"},
        },
    )
    assert artifact.status_code == 200
    artifact_id = artifact.json()["id"]

    status = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "success",
            "handoff": {
                "summary": "task completed with report artifact",
                "details": "report is ready for downstream step",
                "next_actions": ["dispatch dependent task"],
                "open_questions": ["none"],
                "artifacts": [
                    {
                        "artifact_id": artifact_id,
                        "is_required": True,
                        "note": "required downstream input",
                    }
                ],
            },
        },
    )
    assert status.status_code == 200
    assert status.json()["status"] == "success"

    handoff = client.get(f"/tasks/{task_id}/handoff")
    assert handoff.status_code == 200
    handoff_body = handoff.json()
    assert handoff_body["task_id"] == task_id
    assert handoff_body["run_id"] == run_id
    assert handoff_body["summary"] == "task completed with report artifact"
    assert handoff_body["artifacts"][0]["artifact_id"] == artifact_id
    assert handoff_body["artifacts"][0]["is_required"] is True

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert audit.json()["handoff"]["summary"] == "task completed with report artifact"

    events = client.get(f"/events?task_id={task_id}&event_type=task.handoff_published&limit=100")
    assert events.status_code == 200
    assert any(
        artifact_id in item["payload"].get("required_artifact_ids", [])
        for item in events.json()
    )


def test_task_completion_handoff_rejects_unknown_artifact_reference() -> None:
    role_id = _create_role("handoff-invalid-artifact-role")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "handoff invalid artifact task",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post("/workflow-runs", json={"task_ids": [task_id], "initiated_by": "handoff-invalid"})
    assert run.status_code == 200

    assert client.post(f"/tasks/{task_id}/dispatch").status_code == 200

    status = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "success",
            "handoff": {
                "summary": "attempt invalid handoff",
                "artifacts": [{"artifact_id": 999999, "is_required": True}],
            },
        },
    )
    assert status.status_code == 422
    assert "handoff artifact 999999 not found" in status.json()["detail"]
