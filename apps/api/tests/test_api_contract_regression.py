from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _create_role(name: str) -> int:
    response = client.post("/roles", json={"name": name, "context7_enabled": True})
    assert response.status_code == 200
    return response.json()["id"]


def _stub_runner(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_workflow_run_read_contract_has_additive_fields(monkeypatch) -> None:
    _stub_runner(monkeypatch)
    role_id = _create_role("contract-run-role")

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "contract-run-template",
            "steps": [
                {"step_id": "a", "role_id": role_id, "title": "A", "depends_on": []},
                {"step_id": "b", "role_id": role_id, "title": "B", "depends_on": ["a"]},
            ],
        },
    )
    assert workflow.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow.json()["id"], "initiated_by": "contract-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    run_read = client.get(f"/workflow-runs/{run_id}")
    assert run_read.status_code == 200
    payload = run_read.json()

    # Additive modern fields expected by UI/operator workflows
    for key in [
        "failure_categories",
        "failure_triage_hints",
        "suggested_next_actions",
        "duration_ms",
        "success_rate",
        "retries_total",
        "per_role",
        "quality_gate_summary",
    ]:
        assert key in payload


def test_execution_summary_contract_includes_gates_and_timeline(monkeypatch) -> None:
    _stub_runner(monkeypatch)
    role_id = _create_role("contract-summary-role")

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "contract-summary-template",
            "steps": [
                {
                    "step_id": "draft",
                    "role_id": role_id,
                    "title": "Draft",
                    "depends_on": [],
                    "quality_gate_policy": {
                        "required_checks": [
                            {"check": "task-status", "required": True, "severity": "blocker"}
                        ]
                    },
                },
                {
                    "step_id": "review",
                    "role_id": role_id,
                    "title": "Review",
                    "depends_on": ["draft"],
                },
            ],
        },
    )
    assert workflow.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow.json()["id"], "initiated_by": "contract-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    summary = client.get(f"/workflow-runs/{run_id}/execution-summary")
    assert summary.status_code == 200
    body = summary.json()

    for key in [
        "run",
        "task_status_counts",
        "progress_percent",
        "branch_status_cards",
        "next_dispatch",
        "timeline",
        "tasks",
    ]:
        assert key in body

    assert isinstance(body["timeline"], list)
    if body["timeline"]:
        entry = body["timeline"][0]
        for key in ["task_id", "branch", "owner_role_id", "stage", "stage_state", "progress_percent", "blocked_reasons"]:
            assert key in entry

    assert "quality_gate_summary" in body["run"]
