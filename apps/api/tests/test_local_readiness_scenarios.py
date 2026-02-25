from __future__ import annotations

from fastapi.testclient import TestClient

from multyagents_api.local_readiness import (
    run_local_readiness_scenarios,
    run_scenario_a,
    run_scenario_b,
    run_scenario_c,
)
from multyagents_api.main import app


client = TestClient(app)


def _stub_runner_submit(monkeypatch) -> list[dict[str, object]]:
    submissions: list[dict[str, object]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url, **kwargs):  # noqa: ANN001
        if not url.endswith("/tasks/submit"):
            raise AssertionError(f"unexpected runner call: {url}")
        payload = kwargs.get("json")
        if isinstance(payload, dict):
            submissions.append(payload)
        else:
            submissions.append({})
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)
    return submissions


def test_local_readiness_scenario_a_workflow_success(monkeypatch) -> None:
    submissions = _stub_runner_submit(monkeypatch)

    result = run_scenario_a(client, initiated_by="task-061-test")

    assert result["scenario"] == "A"
    assert result["status"] == "success"
    assert result["run_status"] == "success"
    assert len(result["task_ids"]) == 2
    assert len(submissions) == 2


def test_local_readiness_scenario_b_fail_triage_partial_rerun(monkeypatch) -> None:
    submissions = _stub_runner_submit(monkeypatch)

    result = run_scenario_b(client, initiated_by="task-061-test")

    # Partial rerun engine is tracked separately in TASK-057.
    assert result["scenario"] == "B"
    assert result["status"] == "expected_pending"
    assert result["partial_rerun_http_status"] in (200, 404, 405)
    assert result["failed_run_status"] == "failed"
    if "fallback_recovery_run_status" in result:
        assert result["fallback_recovery_run_status"] == "success"
    assert result["triage"]["failure_triage_hints"]
    assert result["triage"]["suggested_next_actions"]
    assert len(submissions) >= 1


def test_local_readiness_scenario_c_approval_handoff_retry_regression(monkeypatch) -> None:
    submissions = _stub_runner_submit(monkeypatch)

    result = run_scenario_c(client, initiated_by="task-061-test")

    assert result["scenario"] == "C"
    assert result["status"] == "success"
    assert result["run_status"] == "success"
    assert result["run_retry_summary"]["total_retries"] >= 1
    assert "network" in result["run_failure_categories"]
    assert "approval.approved" in result["events_sample"]
    assert "task.retry_scheduled" in result["events_sample"]
    assert "task.handoff_published" in result["events_sample"]
    assert len(submissions) == 3


def test_local_readiness_suite_rollup(monkeypatch) -> None:
    _stub_runner_submit(monkeypatch)

    report = run_local_readiness_scenarios(client, initiated_by="task-061-suite")

    assert report["task"] == "TASK-061"
    assert report["summary"]["total"] == 3
    assert report["summary"]["success"] == 2
    assert report["summary"]["expected_pending"] == 1
    assert report["summary"]["overall_status"] == "success"
