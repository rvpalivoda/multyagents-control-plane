from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_list_tasks_returns_created_tasks() -> None:
    role_id = _create_role("tasks-list-role")
    created_1 = client.post("/tasks", json={"role_id": role_id, "title": "task-list-1", "context7_mode": "inherit"})
    created_2 = client.post("/tasks", json={"role_id": role_id, "title": "task-list-2", "context7_mode": "inherit"})
    assert created_1.status_code == 200
    assert created_2.status_code == 200

    listed = client.get("/tasks")
    assert listed.status_code == 200
    titles = {item["title"] for item in listed.json()}
    assert "task-list-1" in titles
    assert "task-list-2" in titles


def test_list_tasks_can_filter_by_run_id() -> None:
    role_id = _create_role("tasks-run-filter-role")
    in_run_task = client.post("/tasks", json={"role_id": role_id, "title": "run-filter-in", "context7_mode": "inherit"}).json()
    out_run_task = client.post("/tasks", json={"role_id": role_id, "title": "run-filter-out", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [in_run_task["id"]], "initiated_by": "test"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    filtered = client.get(f"/tasks?run_id={run_id}")
    assert filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["id"] == in_run_task["id"]
    assert body[0]["id"] != out_run_task["id"]

    missing = client.get("/tasks?run_id=999999")
    assert missing.status_code == 404
