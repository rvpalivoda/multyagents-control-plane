from fastapi.testclient import TestClient

from multyagents_api.main import app


client = TestClient(app)


def test_code_workflow_integration_shared_workspace() -> None:
    role = client.post("/roles", json={"name": "int-code-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    project = client.post(
        "/projects",
        json={
            "name": "int-code-project",
            "root_path": "/tmp/multyagents/int-code",
            "allowed_paths": ["/tmp/multyagents/int-code/src"],
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    workflow_template = client.post(
        "/workflow-templates",
        json={
            "name": "int-code-flow",
            "project_id": project_id,
            "steps": [
                {"step_id": "plan", "role_id": role_id, "title": "Plan", "depends_on": []},
                {"step_id": "build", "role_id": role_id, "title": "Build", "depends_on": ["plan"]},
            ],
        },
    )
    assert workflow_template.status_code == 200
    workflow_template_id = workflow_template.json()["id"]

    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "implement feature",
            "context7_mode": "inherit",
            "execution_mode": "shared-workspace",
            "project_id": project_id,
            "lock_paths": ["/tmp/multyagents/int-code/src/module-a"],
            "requires_approval": False,
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post(
        "/workflow-runs",
        json={
            "workflow_template_id": workflow_template_id,
            "task_ids": [task_id],
            "initiated_by": "integration-test",
        },
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200
    dispatch_body = dispatch.json()
    assert dispatch_body["resolved_context7_enabled"] is True
    assert dispatch_body["runner_payload"]["execution_mode"] == "shared-workspace"
    assert dispatch_body["runner_payload"]["workspace"]["project_id"] == project_id
    assert dispatch_body["runner_payload"]["workspace"]["lock_paths"] == ["/tmp/multyagents/int-code/src/module-a"]

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    audit_body = audit.json()
    assert audit_body["execution_mode"] == "shared-workspace"
    assert audit_body["requires_approval"] is False
    assert audit_body["approval_status"] is None

    run_events = client.get(f"/events?run_id={run_id}&limit=100")
    assert run_events.status_code == 200
    run_event_types = [item["event_type"] for item in run_events.json()]
    assert "workflow_run.created" in run_event_types
    assert "task.dispatched" in run_event_types


def test_text_workflow_integration_with_approval_gate() -> None:
    role = client.post("/roles", json={"name": "int-text-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "write release notes",
            "context7_mode": "force_off",
            "execution_mode": "no-workspace",
            "requires_approval": True,
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post(
        "/workflow-runs",
        json={"task_ids": [task_id], "initiated_by": "integration-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    blocked_dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert blocked_dispatch.status_code == 409
    assert "status=pending" in blocked_dispatch.json()["detail"]

    approval = client.get(f"/tasks/{task_id}/approval")
    assert approval.status_code == 200
    approval_id = approval.json()["id"]
    assert approval.json()["status"] == "pending"

    approved = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor": "integration-reviewer", "comment": "ok"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    dispatched = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatched.status_code == 200
    dispatched_body = dispatched.json()
    assert dispatched_body["resolved_context7_enabled"] is False
    assert dispatched_body["runner_payload"]["execution_mode"] == "no-workspace"

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    audit_body = audit.json()
    assert audit_body["requires_approval"] is True
    assert audit_body["approval_status"] == "approved"
    assert audit_body["resolved_context7_enabled"] is False

    task_events = client.get(f"/events?task_id={task_id}&limit=100")
    assert task_events.status_code == 200
    task_event_types = [item["event_type"] for item in task_events.json()]
    assert "approval.pending" in task_event_types
    assert "task.dispatch_blocked_by_approval" in task_event_types
    assert "approval.approved" in task_event_types
    assert "task.dispatched" in task_event_types

    run_events = client.get(f"/events?run_id={run_id}&limit=100")
    assert run_events.status_code == 200
    assert any(item["event_type"] == "workflow_run.created" for item in run_events.json())


def test_code_workflow_integration_docker_sandbox() -> None:
    role = client.post("/roles", json={"name": "int-docker-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    project = client.post(
        "/projects",
        json={
            "name": "int-docker-project",
            "root_path": "/tmp/multyagents/int-docker",
            "allowed_paths": ["/tmp/multyagents/int-docker/src"],
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    task = client.post(
        "/tasks",
        json={
            "role_id": role_id,
            "title": "run docker integration",
            "context7_mode": "inherit",
            "execution_mode": "docker-sandbox",
            "project_id": project_id,
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo integration docker"],
                "workdir": "/workspace/project",
            },
        },
    )
    assert task.status_code == 200
    task_id = task.json()["id"]

    run = client.post(
        "/workflow-runs",
        json={"task_ids": [task_id], "initiated_by": "integration-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    dispatch = client.post(f"/tasks/{task_id}/dispatch")
    assert dispatch.status_code == 200
    dispatch_body = dispatch.json()
    assert dispatch_body["runner_payload"]["execution_mode"] == "docker-sandbox"
    assert dispatch_body["runner_payload"]["sandbox"]["image"] == "alpine:3.20"
    assert dispatch_body["runner_payload"]["sandbox"]["mounts"] == [
        {
            "source": "/tmp/multyagents/int-docker/src",
            "target": "/workspace/project",
            "read_only": False,
        }
    ]

    runner_success = client.post(
        f"/runner/tasks/{task_id}/status",
        json={
            "status": "success",
            "message": "docker completed",
            "exit_code": 0,
            "container_id": f"multyagents-{task_id}",
        },
    )
    assert runner_success.status_code == 200
    assert runner_success.json()["status"] == "success"

    audit = client.get(f"/tasks/{task_id}/audit")
    assert audit.status_code == 200
    audit_body = audit.json()
    assert audit_body["sandbox_image"] == "alpine:3.20"
    assert audit_body["sandbox_workdir"] == "/workspace/project"
    assert audit_body["sandbox_container_id"] == f"multyagents-{task_id}"
    assert audit_body["sandbox_exit_code"] == 0

    run_events = client.get(f"/events?run_id={run_id}&limit=100")
    assert run_events.status_code == 200
    run_event_types = [item["event_type"] for item in run_events.json()]
    assert "workflow_run.created" in run_event_types
    assert "task.runner_status_updated" in run_event_types


def test_workflow_integration_artifact_handoff_chain() -> None:
    role = client.post("/roles", json={"name": "int-handoff-role", "context7_enabled": True})
    assert role.status_code == 200
    role_id = role.json()["id"]

    workflow_template = client.post(
        "/workflow-templates",
        json={
            "name": "int-handoff-flow",
            "steps": [
                {"step_id": "code", "role_id": role_id, "title": "Code", "depends_on": []},
                {
                    "step_id": "report",
                    "role_id": role_id,
                    "title": "Report",
                    "depends_on": ["code"],
                    "required_artifacts": [
                        {"from_step_id": "code", "artifact_type": "report", "label": "handoff"}
                    ],
                },
            ],
        },
    )
    assert workflow_template.status_code == 200
    workflow_template_id = workflow_template.json()["id"]

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow_template_id, "initiated_by": "integration-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    code_task_id = run.json()["task_ids"][0]
    report_task_id = run.json()["task_ids"][1]

    code_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert code_dispatch.status_code == 200
    assert code_dispatch.json()["dispatched"] is True
    assert code_dispatch.json()["task_id"] == code_task_id

    code_success = client.post(f"/runner/tasks/{code_task_id}/status", json={"status": "success"})
    assert code_success.status_code == 200

    blocked_report = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert blocked_report.status_code == 200
    assert blocked_report.json()["dispatched"] is False
    assert blocked_report.json()["reason"] == "artifacts not satisfied"

    handoff_artifact = client.post(
        "/artifacts",
        json={
            "artifact_type": "report",
            "location": "/tmp/multyagents/int-handoff/report.md",
            "summary": "handoff report",
            "producer_task_id": code_task_id,
            "run_id": run_id,
            "metadata": {"label": "handoff"},
        },
    )
    assert handoff_artifact.status_code == 200
    handoff_artifact_id = handoff_artifact.json()["id"]

    report_dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert report_dispatch.status_code == 200
    assert report_dispatch.json()["dispatched"] is True
    assert report_dispatch.json()["task_id"] == report_task_id

    report_audit = client.get(f"/tasks/{report_task_id}/audit")
    assert report_audit.status_code == 200
    assert handoff_artifact_id in report_audit.json()["consumed_artifact_ids"]


def test_workflow_dispatch_payload_includes_resolved_role_skill_packs() -> None:
    skill_pack = client.post(
        "/skill-packs",
        json={
            "name": "int-dispatch-pack",
            "skills": ["skills/task-governance", "skills/api-orchestrator-fastapi"],
        },
    )
    assert skill_pack.status_code == 200

    role = client.post(
        "/roles",
        json={
            "name": "int-dispatch-role",
            "context7_enabled": True,
            "skill_packs": ["int-dispatch-pack"],
        },
    )
    assert role.status_code == 200
    role_id = role.json()["id"]

    workflow_template = client.post(
        "/workflow-templates",
        json={
            "name": "int-dispatch-skill-flow",
            "steps": [
                {"step_id": "single", "role_id": role_id, "title": "Single step", "depends_on": []},
            ],
        },
    )
    assert workflow_template.status_code == 200

    run = client.post(
        "/workflow-runs",
        json={"workflow_template_id": workflow_template.json()["id"], "initiated_by": "integration-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]
    task_id = run.json()["task_ids"][0]

    dispatch = client.post(f"/workflow-runs/{run_id}/dispatch-ready")
    assert dispatch.status_code == 200
    assert dispatch.json()["dispatched"] is True
    assert dispatch.json()["task_id"] == task_id
    assert dispatch.json()["dispatch"]["runner_payload"]["role_skill_packs"] == ["int-dispatch-pack"]
