from fastapi.testclient import TestClient
import pytest

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _mock_runner_submit_success(monkeypatch) -> None:  # noqa: ANN001
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def _mock_runner_submit_fail_first_then_succeed(monkeypatch) -> None:  # noqa: ANN001
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    attempts = {"count": 0}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("runner unavailable")
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_workflow_run_transitions_to_success_when_all_tasks_succeed(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    role_id = _create_role("rollup-success-role")
    task_1 = client.post("/tasks", json={"role_id": role_id, "title": "rollup-1", "context7_mode": "inherit"}).json()
    task_2 = client.post("/tasks", json={"role_id": role_id, "title": "rollup-2", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [task_1["id"], task_2["id"]], "initiated_by": "test"}).json()

    assert client.post(f"/tasks/{task_1['id']}/dispatch").status_code == 200
    assert client.post(f"/tasks/{task_2['id']}/dispatch").status_code == 200
    assert client.post(f"/runner/tasks/{task_1['id']}/status", json={"status": "success"}).status_code == 200
    assert client.post(f"/runner/tasks/{task_2['id']}/status", json={"status": "success"}).status_code == 200

    current_run = client.get(f"/workflow-runs/{run['id']}")
    assert current_run.status_code == 200
    assert current_run.json()["status"] == "success"


def test_workflow_run_transitions_to_failed_on_task_failure(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    role_id = _create_role("rollup-failed-role")
    task = client.post("/tasks", json={"role_id": role_id, "title": "rollup-fail", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [task["id"]], "initiated_by": "test"}).json()

    assert client.post(f"/tasks/{task['id']}/dispatch").status_code == 200
    assert client.post(f"/runner/tasks/{task['id']}/status", json={"status": "failed"}).status_code == 200

    current_run = client.get(f"/workflow-runs/{run['id']}")
    assert current_run.status_code == 200
    assert current_run.json()["status"] == "failed"


def test_workflow_run_rollup_includes_duration_success_rate_and_per_role_metrics(monkeypatch) -> None:
    _mock_runner_submit_success(monkeypatch)

    builder_role_id = _create_role("rollup-metrics-builder-role")
    reviewer_role_id = _create_role("rollup-metrics-reviewer-role")
    task_1 = client.post("/tasks", json={"role_id": builder_role_id, "title": "metrics-1", "context7_mode": "inherit"}).json()
    task_2 = client.post("/tasks", json={"role_id": builder_role_id, "title": "metrics-2", "context7_mode": "inherit"}).json()
    task_3 = client.post("/tasks", json={"role_id": reviewer_role_id, "title": "metrics-3", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [task_1["id"], task_2["id"], task_3["id"]], "initiated_by": "metrics"}).json()

    assert client.post(f"/tasks/{task_1['id']}/dispatch").status_code == 200
    assert client.post(f"/tasks/{task_2['id']}/dispatch").status_code == 200
    assert client.post(f"/tasks/{task_3['id']}/dispatch").status_code == 200

    assert (
        client.post(
            f"/runner/tasks/{task_1['id']}/status",
            json={"status": "success", "started_at": "2026-02-25T10:00:00Z", "finished_at": "2026-02-25T10:00:10Z"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/runner/tasks/{task_2['id']}/status",
            json={"status": "failed", "started_at": "2026-02-25T10:00:00Z", "finished_at": "2026-02-25T10:00:20Z"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/runner/tasks/{task_3['id']}/status",
            json={"status": "success", "started_at": "2026-02-25T10:00:05Z", "finished_at": "2026-02-25T10:00:25Z"},
        ).status_code
        == 200
    )

    run_body = client.get(f"/workflow-runs/{run['id']}").json()
    assert run_body["status"] == "failed"
    assert run_body["duration_ms"] == 25000
    assert run_body["retries_total"] == 0
    assert run_body["success_rate"] == pytest.approx(66.67)
    assert len(run_body["per_role"]) == 2

    builder_metric = next(item for item in run_body["per_role"] if item["role_id"] == builder_role_id)
    reviewer_metric = next(item for item in run_body["per_role"] if item["role_id"] == reviewer_role_id)

    assert builder_metric == {
        "role_id": builder_role_id,
        "task_count": 2,
        "successful_tasks": 1,
        "failed_tasks": 1,
        "throughput_tasks": 2,
        "success_rate": 50.0,
        "retries_total": 0,
        "duration_ms": 30000,
    }
    assert reviewer_metric == {
        "role_id": reviewer_role_id,
        "task_count": 1,
        "successful_tasks": 1,
        "failed_tasks": 0,
        "throughput_tasks": 1,
        "success_rate": 100.0,
        "retries_total": 0,
        "duration_ms": 20000,
    }


def test_workflow_run_rollup_counts_retry_after_resubmission(monkeypatch) -> None:
    _mock_runner_submit_fail_first_then_succeed(monkeypatch)

    role_id = _create_role("rollup-retry-role")
    task = client.post("/tasks", json={"role_id": role_id, "title": "retry-metrics", "context7_mode": "inherit"}).json()
    run = client.post("/workflow-runs", json={"task_ids": [task["id"]], "initiated_by": "metrics-retry"}).json()

    first_dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert first_dispatch.status_code == 200
    assert client.get(f"/tasks/{task['id']}").json()["status"] == "submit-failed"

    second_dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert second_dispatch.status_code == 200

    assert (
        client.post(
            f"/runner/tasks/{task['id']}/status",
            json={"status": "success", "started_at": "2026-02-25T11:00:00Z", "finished_at": "2026-02-25T11:00:15Z"},
        ).status_code
        == 200
    )

    run_body = client.get(f"/workflow-runs/{run['id']}").json()
    assert run_body["status"] == "success"
    assert run_body["duration_ms"] == 15000
    assert run_body["success_rate"] == 100.0
    assert run_body["retries_total"] == 1
    assert run_body["per_role"][0]["retries_total"] == 1
