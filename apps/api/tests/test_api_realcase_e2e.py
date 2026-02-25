from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def _stub_runner_submit(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _Response()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)


def test_realcase_project_path_create_and_run_success(monkeypatch) -> None:
    _stub_runner_submit(monkeypatch)

    project = client.post(
        "/projects",
        json={
            "name": "realcase-project-alpha",
            "root_path": "/tmp/multyagents-e2e-real/project-alpha",
            "allowed_paths": [
                "/tmp/multyagents-e2e-real/project-alpha/src",
                "/tmp/multyagents-e2e-real/project-alpha/docs",
            ],
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    role = client.post("/roles", json={"name": "realcase-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "realcase-bugfix-lane",
            "project_id": project_id,
            "steps": [
                {"step_id": "diagnose", "role_id": role_id, "title": "Diagnose", "depends_on": []},
                {"step_id": "fix", "role_id": role_id, "title": "Fix", "depends_on": ["diagnose"]},
            ],
        },
    )
    assert workflow.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow.json()["id"], "initiated_by": "realcase-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    # step 1
    dispatch1 = client.post(f"/workflow-runs/{run_id}/dispatch-ready", json={})
    assert dispatch1.status_code == 200
    assert dispatch1.json()["dispatched"] is True
    task1 = dispatch1.json()["task_id"]

    status1 = client.post(
        f"/runner/tasks/{task1}/status",
        json={"status": "success", "message": "diagnose done"},
    )
    assert status1.status_code == 200

    # step 2
    dispatch2 = client.post(f"/workflow-runs/{run_id}/dispatch-ready", json={})
    assert dispatch2.status_code == 200
    assert dispatch2.json()["dispatched"] is True
    task2 = dispatch2.json()["task_id"]

    status2 = client.post(
        f"/runner/tasks/{task2}/status",
        json={"status": "success", "message": "fix done"},
    )
    assert status2.status_code == 200

    final_run = client.get(f"/workflow-runs/{run_id}")
    assert final_run.status_code == 200
    assert final_run.json()["status"] == "success"


def test_realcase_fail_triage_and_partial_rerun_behavior(monkeypatch) -> None:
    _stub_runner_submit(monkeypatch)

    role = client.post("/roles", json={"name": "realcase-triage-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    workflow = client.post(
        "/workflow-templates",
        json={
            "name": "realcase-partial-rerun",
            "steps": [{"step_id": "only", "role_id": role_id, "title": "Only step", "depends_on": []}],
        },
    )
    assert workflow.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow.json()["id"], "initiated_by": "realcase-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    task_id = run.json()["task_ids"][0]

    dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready", json={})
    assert dispatch.status_code == 200
    assert dispatch.json()["dispatched"] is True

    failed = client.post(
        f"/runner/tasks/{task_id}/status",
        json={"status": "failed", "message": "permission denied writing workspace"},
    )
    assert failed.status_code == 200
    failed_payload = failed.json()
    assert failed_payload["failure_category"] in {"permission", "workspace-git", "unknown"}
    assert isinstance(failed_payload["failure_triage_hints"], list)
    assert isinstance(failed_payload["suggested_next_actions"], list)

    rerun = client.post(
        f"/workflow-runs/{run_id}/partial-rerun",
        json={
            "task_ids": [task_id],
            "requested_by": "realcase-operator",
            "reason": "retry after permissions fix",
            "auto_dispatch": True,
            "max_dispatch": 3,
        },
    )
    assert rerun.status_code == 200
    body = rerun.json()
    assert body["run_id"] == run_id
    assert task_id in body["reset_task_ids"]
    assert isinstance(body["aggregate"], dict)
