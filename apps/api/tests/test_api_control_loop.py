from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def test_control_loop_plans_parallel_spawn_and_reports_partial_failures(monkeypatch) -> None:
    submit_payloads: list[dict[str, object]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if not url.endswith("/tasks/submit"):
            raise AssertionError(f"unexpected runner call: {url}")
        payload = kwargs["json"]
        submit_payloads.append(payload)
        if payload["prompt"] == "Root B":
            raise RuntimeError("runner offline")
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role("control-loop-role-a")
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "control-loop-template-a",
            "steps": [
                {"step_id": "root_a", "role_id": role_id, "title": "Root A", "depends_on": []},
                {"step_id": "root_b", "role_id": role_id, "title": "Root B", "depends_on": []},
                {"step_id": "merge", "role_id": role_id, "title": "Merge", "depends_on": ["root_a", "root_b"]},
            ],
        },
    )
    assert workflow.status_code == 200
    workflow_id = workflow.json()["id"]

    run = client.post("/workflow-runs", json={"workflow_template_id": workflow_id, "initiated_by": "control-loop-test"})
    assert run.status_code == 200
    run_id = run.json()["id"]

    loop = client.post(f"/workflow-runs/{run_id}/control-loop", json={"max_dispatch": 10})
    assert loop.status_code == 200
    loop_body = loop.json()
    assert loop_body["run_id"] == run_id
    assert [item["task_id"] for item in loop_body["plan"]["ready"]] == run.json()["task_ids"][:2]
    assert len(loop_body["spawn"]) == 2
    assert len(submit_payloads) == 2

    submitted_item = next(item for item in loop_body["spawn"] if item["submitted"] is True)
    failed_submit_item = next(item for item in loop_body["spawn"] if item["submitted"] is False)
    assert submitted_item["task_status"] == "queued"
    assert failed_submit_item["task_status"] == "submit-failed"
    assert "runner submit failed" in failed_submit_item["dispatch"]["runner_submission"]["message"]
    assert loop_body["aggregate"]["run"]["status"] == "failed"
    assert failed_submit_item["task_id"] in loop_body["aggregate"]["failed_task_ids"]

    success_update = client.post(
        f"/runner/tasks/{submitted_item['task_id']}/status",
        json={"status": "success"},
    )
    assert success_update.status_code == 200

    summary = client.get(f"/workflow-runs/{run_id}/execution-summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["partial_completion"] is True
    assert submitted_item["task_id"] in summary_body["successful_task_ids"]
    assert failed_submit_item["task_id"] in summary_body["failed_task_ids"]
    merge_task_id = run.json()["task_ids"][2]
    assert merge_task_id in summary_body["pending_task_ids"]


def test_control_loop_blocks_approval_gates_and_summary_reflects_plan(monkeypatch) -> None:
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

    role_id = _create_role("control-loop-role-b")
    normal_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "No Approval",
            "execution_mode": "no-workspace",
        },
    )
    assert normal_task.status_code == 200
    approval_task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "Needs Approval",
            "execution_mode": "no-workspace",
            "requires_approval": True,
        },
    )
    assert approval_task.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"task_ids": [normal_task.json()["id"], approval_task.json()["id"]], "initiated_by": "approval-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    first_loop = client.post(f"/workflow-runs/{run_id}/control-loop", json={"max_dispatch": 10})
    assert first_loop.status_code == 200
    first_loop_body = first_loop.json()
    assert [item["task_id"] for item in first_loop_body["plan"]["ready"]] == [normal_task.json()["id"]]
    blocked = first_loop_body["plan"]["blocked"]
    assert any(
        item["task_id"] == approval_task.json()["id"] and item["reason"] == "approval-required"
        for item in blocked
    )

    approval = client.get(f"/tasks/{approval_task.json()['id']}/approval")
    assert approval.status_code == 200
    approval_id = approval.json()["id"]
    approved = client.post(f"/approvals/{approval_id}/approve", json={"actor": "operator", "comment": "approved"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    first_task_success = client.post(
        f"/runner/tasks/{normal_task.json()['id']}/status",
        json={"status": "success"},
    )
    assert first_task_success.status_code == 200

    second_loop = client.post(f"/workflow-runs/{run_id}/control-loop", json={"max_dispatch": 10})
    assert second_loop.status_code == 200
    second_loop_body = second_loop.json()
    assert [item["task_id"] for item in second_loop_body["plan"]["ready"]] == [approval_task.json()["id"]]
    assert len(second_loop_body["spawn"]) == 1
    assert second_loop_body["spawn"][0]["submitted"] is True

    second_task_success = client.post(
        f"/runner/tasks/{approval_task.json()['id']}/status",
        json={"status": "success"},
    )
    assert second_task_success.status_code == 200

    summary = client.get(f"/workflow-runs/{run_id}/execution-summary")
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["run"]["status"] == "success"
    assert summary_body["task_status_counts"]["success"] == 2
    assert summary_body["next_dispatch"]["ready"] == []
