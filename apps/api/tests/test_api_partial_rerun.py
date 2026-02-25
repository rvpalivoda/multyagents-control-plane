from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_partial_rerun_by_step_ids_resets_only_selected_failed_branch(monkeypatch) -> None:
    submit_calls: list[dict[str, object]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if url.endswith("/tasks/submit"):
            submit_calls.append(kwargs["json"])
            return _Response()
        raise AssertionError(f"unexpected runner call: {url}")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("partial-rerun-role-steps")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "partial-rerun-steps-template",
            "steps": [
                {"step_id": "root_a", "role_id": role_id, "title": "Root A", "depends_on": []},
                {"step_id": "root_b", "role_id": role_id, "title": "Root B", "depends_on": []},
            ],
        },
    )
    assert workflow.status_code == 200
    workflow_id = workflow.json()["id"]

    run = client.post("/workflow-runs", json={"workflow_template_id": workflow_id, "initiated_by": "partial-rerun-test"})
    assert run.status_code == 200
    run_id = run.json()["id"]
    first_task_id = run.json()["task_ids"][0]
    second_task_id = run.json()["task_ids"][1]

    first_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert first_dispatch.status_code == 200
    assert first_dispatch.json()["task_id"] == first_task_id
    first_failed = client.post(
        f"/runner/tasks/{first_task_id}/status",
        json={"status": "failed", "message": "network timeout"},
    )
    assert first_failed.status_code == 200

    second_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert second_dispatch.status_code == 200
    assert second_dispatch.json()["task_id"] == second_task_id
    second_success = client.post(
        f"/runner/tasks/{second_task_id}/status",
        json={"status": "success", "message": "done"},
    )
    assert second_success.status_code == 200

    rerun = client.post(
        f"/workflow-runs/{run_id}/partial-rerun",
        json={
            "step_ids": ["root_a"],
            "requested_by": "operator-ui",
            "reason": "applied fix for transient failure",
            "auto_dispatch": True,
            "max_dispatch": 5,
        },
    )
    assert rerun.status_code == 200
    body = rerun.json()
    assert body["selected_step_ids"] == ["root_a"]
    assert body["selected_task_ids"] == [first_task_id]
    assert body["reset_task_ids"] == [first_task_id]
    assert len(body["spawn"]) == 1
    assert body["spawn"][0]["task_id"] == first_task_id
    assert body["spawn"][0]["submitted"] is True

    first_task = client.get(f"/tasks/{first_task_id}")
    assert first_task.status_code == 200
    assert first_task.json()["status"] == "queued"
    second_task = client.get(f"/tasks/{second_task_id}")
    assert second_task.status_code == 200
    assert second_task.json()["status"] == "success"

    first_audit = client.get(f"/tasks/{first_task_id}/audit")
    assert first_audit.status_code == 200
    assert first_audit.json()["rerun_count"] == 1
    assert first_audit.json()["last_rerun_by"] == "operator-ui"
    assert first_audit.json()["last_rerun_reason"] == "applied fix for transient failure"
    assert first_audit.json()["last_rerun_at"] is not None

    rerun_events = client.get(f"/events?run_id={run_id}&event_type=workflow_run.partial_rerun_requested&limit=20")
    assert rerun_events.status_code == 200
    assert rerun_events.json()
    payload = rerun_events.json()[-1]["payload"]
    assert payload["requested_by"] == "operator-ui"
    assert payload["reason"] == "applied fix for transient failure"
    assert payload["selected_task_ids"] == [first_task_id]


def test_partial_rerun_rejects_non_failed_task_selection(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if url.endswith("/tasks/submit"):
            return _Response()
        raise AssertionError(f"unexpected runner call: {url}")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("partial-rerun-role-invalid")
    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "already successful task",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]
    run = client.post("/workflow-runs", json={"task_ids": [task_id], "initiated_by": "partial-rerun-invalid"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200
    success = client.post(f"/runner/tasks/{task_id}/status", json={"status": "success"})
    assert success.status_code == 200

    rerun = client.post(
        f"/workflow-runs/{run_id}/partial-rerun",
        json={
            "task_ids": [task_id],
            "requested_by": "operator-ui",
            "reason": "should fail validation",
        },
    )
    assert rerun.status_code == 422
    assert "failed terminal tasks only" in rerun.text


def test_partial_rerun_rejects_when_run_has_active_tasks(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if url.endswith("/tasks/submit"):
            return _Response()
        raise AssertionError(f"unexpected runner call: {url}")

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("partial-rerun-role-active")
    first_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "failed branch",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert first_task.status_code == 200
    second_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "still running branch",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert second_task.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"task_ids": [first_task.json()["id"], second_task.json()["id"]], "initiated_by": "partial-rerun-active"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    first_task_id = first_task.json()["id"]
    second_task_id = second_task.json()["id"]

    assert client.post(f"/tasks/{first_task_id}/dispatch").status_code == 200
    assert client.post(f"/runner/tasks/{first_task_id}/status", json={"status": "failed", "message": "failed"}).status_code == 200

    assert client.post(f"/tasks/{second_task_id}/dispatch").status_code == 200
    assert client.post(f"/runner/tasks/{second_task_id}/status", json={"status": "running", "message": "in progress"}).status_code == 200

    rerun = client.post(
        f"/workflow-runs/{run_id}/partial-rerun",
        json={
            "task_ids": [first_task_id],
            "requested_by": "operator-ui",
            "reason": "should be blocked while another task is active",
        },
    )
    assert rerun.status_code == 409
    assert "active tasks" in rerun.text
