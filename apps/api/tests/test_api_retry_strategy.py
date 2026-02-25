from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str, *, retry_policy: dict[str, object]) -> int:
    response = client.post(
        "/roles",
        json={
            "name": name,
            "context7_enabled": True,
            "execution_constraints": {"retry_policy": retry_policy},
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_retry_policy_retries_transient_runner_failure_without_breaking_handoff(monkeypatch) -> None:
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

    role_id = _create_role(
        "retry-policy-handoff-role",
        retry_policy={"max_retries": 2, "retry_on": ["network", "runner-transient"]},
    )
    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "retry-handoff-template",
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Plan", "depends_on": []},
                {
                    "step_id": "report",
                    "role_id": role_id,
                    "title": "Report",
                    "depends_on": ["plan"],
                    "required_artifacts": [
                        {"from_step_id": "plan", "artifact_type": "report", "label": "handoff"}
                    ],
                },
            ],
        },
    )
    assert workflow.status_code == 200
    workflow_id = workflow.json()["id"]

    run = client.post("/workflow-runs", json={"workflow_template_id": workflow_id, "initiated_by": "retry-test"})
    assert run.status_code == 200
    run_id = run.json()["id"]
    first_task_id = run.json()["task_ids"][0]
    second_task_id = run.json()["task_ids"][1]

    first_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert first_dispatch.status_code == 200
    assert first_dispatch.json()["dispatched"] is True
    assert first_dispatch.json()["task_id"] == first_task_id
    assert len(submit_calls) == 1

    transient_failure = client.post(
        f"/runner/tasks/{first_task_id}/status",
        json={"status": "failed", "message": "network timeout during dependency fetch"},
    )
    assert transient_failure.status_code == 200
    assert transient_failure.json()["status"] == "created"

    first_audit = client.get(f"/tasks/{first_task_id}/audit")
    assert first_audit.status_code == 200
    assert first_audit.json()["retry_attempts"] == 1
    assert "network" in first_audit.json()["failure_categories"]
    assert first_audit.json()["last_retry_reason"] is not None

    retry_event = client.get(
        f"/events?task_id={first_task_id}&event_type=task.retry_scheduled&limit=20"
    )
    assert retry_event.status_code == 200
    assert any(item["payload"].get("failure_category") == "network" for item in retry_event.json())

    retry_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert retry_dispatch.status_code == 200
    assert retry_dispatch.json()["dispatched"] is True
    assert retry_dispatch.json()["task_id"] == first_task_id
    assert len(submit_calls) == 2

    required_artifact = client.post(
        "/artifacts",
        json={
            "artifact_type": "report",
            "location": "/tmp/multyagents/retry/handoff.md",
            "summary": "retry handoff output",
            "producer_task_id": first_task_id,
            "run_id": run_id,
            "metadata": {"label": "handoff"},
        },
    )
    assert required_artifact.status_code == 200
    handoff_artifact_id = required_artifact.json()["id"]

    first_success = client.post(
        f"/runner/tasks/{first_task_id}/status",
        json={
            "status": "success",
            "handoff": {
                "summary": "retry completed",
                "next_actions": ["dispatch report"],
                "artifacts": [
                    {
                        "artifact_id": handoff_artifact_id,
                        "is_required": True,
                        "note": "handoff after retry",
                    }
                ],
            },
        },
    )
    assert first_success.status_code == 200
    assert first_success.json()["status"] == "success"

    second_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert second_dispatch.status_code == 200
    assert second_dispatch.json()["dispatched"] is True
    assert second_dispatch.json()["task_id"] == second_task_id

    second_success = client.post(
        f"/runner/tasks/{second_task_id}/status",
        json={"status": "success", "message": "done"},
    )
    assert second_success.status_code == 200

    run_status = client.get(f"/workflow-runs/{run_id}")
    assert run_status.status_code == 200
    assert run_status.json()["status"] == "success"
    assert run_status.json()["retry_summary"]["total_retries"] == 1
    assert "network" in run_status.json()["failure_categories"]
    assert run_status.json()["failure_triage_hints"]


def test_retry_policy_retries_transient_runner_submit_failures(monkeypatch) -> None:
    submit_attempts = {"count": 0}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if not url.endswith("/tasks/submit"):
            raise AssertionError(f"unexpected runner call: {url}")
        submit_attempts["count"] += 1
        if submit_attempts["count"] == 1:
            raise RuntimeError("service unavailable")
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role_id = _create_role(
        "retry-policy-submit-role",
        retry_policy={"max_retries": 2, "retry_on": ["runner-transient"]},
    )
    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "submit-retry-task",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    first_dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert first_dispatch.status_code == 200
    first_task = client.get(f"/tasks/{task_id}")
    assert first_task.status_code == 200
    assert first_task.json()["status"] == "created"

    retry_event = client.get(
        f"/events?task_id={task_id}&event_type=task.retry_scheduled&limit=20"
    )
    assert retry_event.status_code == 200
    assert retry_event.json()
    assert retry_event.json()[-1]["payload"]["trigger_status"] == "submit-failed"

    second_dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert second_dispatch.status_code == 200
    second_task = client.get(f"/tasks/{task_id}")
    assert second_task.status_code == 200
    assert second_task.json()["status"] == "queued"

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert audit.json()["retry_attempts"] == 1
    assert "runner-transient" in audit.json()["failure_categories"]


def test_retry_policy_does_not_retry_non_transient_failures(monkeypatch) -> None:
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

    role_id = _create_role(
        "retry-policy-no-retry-role",
        retry_policy={"max_retries": 2, "retry_on": ["network"]},
    )
    created = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "no-retry-task",
            "context7_mode": "inherit",
            "execution_mode": "no-workspace",
        },
    )
    assert created.status_code == 200
    task_id = created.json()["id"]

    assert client.post(f"/tasks/{task_id}/dispatch").status_code == 200
    failed = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "failed", "message": "syntax error in generated code"},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    retry_events = client.get(f"/events?task_id={task_id}&event_type=task.retry_scheduled&limit=20")
    assert retry_events.status_code == 200
    assert retry_events.json() == []

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    assert audit.json()["retry_attempts"] == 0
    assert audit.json()["last_retry_reason"] == "retry policy skipped: failure category is not transient"
