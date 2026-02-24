from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _create_task(role_id: int, title: str) -> int:
    response = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": title,
            "context7_mode": "inherit",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_workflow_run_lifecycle_and_events() -> None:
    role_id = _create_role("timeline-role")
    task_id = _create_task(role_id, "timeline-task")

    created = client.post(
        "/workflow-runs",
        json={"task_ids": [task_id], "initiated_by": "ui"},
    )
    assert created.status_code == 200
    run = created.json()
    run_id = run["id"]
    assert run["status"] == "created"

    listed = client.get("/workflow-runs")
    assert listed.status_code == 200
    assert run_id in {item["id"] for item in listed.json()}

    paused = client.post(f"/workflow-runs/{run_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    resumed = client.post(f"/workflow-runs/{run_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "running"

    aborted = client.post(f"/workflow-runs/{run_id}/abort")
    assert aborted.status_code == 200
    assert aborted.json()["status"] == "aborted"

    resume_after_abort = client.post(f"/workflow-runs/{run_id}/resume")
    assert resume_after_abort.status_code == 409

    events_for_run = client.get(f"/events?run_id={run_id}&limit=50")
    assert events_for_run.status_code == 200
    event_types = [event["event_type"] for event in events_for_run.json()]
    assert "workflow_run.created" in event_types
    assert "workflow_run.paused" in event_types
    assert "workflow_run.resumed" in event_types
    assert "workflow_run.aborted" in event_types


def test_events_can_be_filtered_by_task_id() -> None:
    role_id = _create_role("timeline-task-filter")
    task_id = _create_task(role_id, "task-filter")

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200

    events = client.get(f"/events?task_id={task_id}&limit=20")
    assert events.status_code == 200
    body = events.json()
    assert len(body) >= 2
    assert all(event["task_id"] == task_id for event in body)
    assert any(event["event_type"] == "task.created" for event in body)
    assert any(event["event_type"] == "task.dispatched" for event in body)


def test_create_workflow_run_requires_input() -> None:
    response = client.post("/workflow-runs", json={})
    assert response.status_code == 422
