from types import MethodType

from fastapi.testclient import TestClient

from multyagents_api.main import app, store


client = TestClient(app)


def test_contract_version_endpoint() -> None:
    response = client.get("/contracts/current")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "v1"
    assert body["schema_file"] == "packages/contracts/v1/context7.schema.json"


def test_dispatch_inherits_role_context7_setting() -> None:
    role = client.post("/roles", json={"name": "coder", "context7_enabled": True}).json()
    task = client.post(
        "/tasks",
        json={"role_id": role["id"], "title": "implement api", "context7_mode": "inherit"},
    ).json()
    assert task["execution_mode"] == "no-workspace"
    assert task["requires_approval"] is False

    dispatched = client.post(f"/tasks/{task['id']}/dispatch")
    assert dispatched.status_code == 200
    body = dispatched.json()

    assert body["resolved_context7_enabled"] is True
    assert body["runner_payload"]["context"]["provider"] == "context7"
    assert body["runner_payload"]["context"]["enabled"] is True
    assert body["runner_payload"]["execution_mode"] == "no-workspace"
    assert body["runner_payload"]["workspace"] is None
    assert body["runner_submission"]["submitted"] is False

    audit = client.get(f"/tasks/{task['id']}/audit")
    assert audit.status_code == 200
    assert audit.json()["resolved_context7_enabled"] is True
    assert audit.json()["execution_mode"] == "no-workspace"
    assert audit.json()["requires_approval"] is False
    assert audit.json()["approval_status"] is None
    assert audit.json()["project_id"] is None
    assert audit.json()["lock_paths"] == []


def test_dispatch_force_off_overrides_role_context7_setting() -> None:
    role = client.post("/roles", json={"name": "writer", "context7_enabled": True}).json()
    task = client.post(
        "/tasks",
        json={"role_id": role["id"], "title": "write docs", "context7_mode": "force_off"},
    ).json()

    dispatched = client.post(f"/tasks/{task['id']}/dispatch")
    assert dispatched.status_code == 200

    body = dispatched.json()
    assert body["resolved_context7_enabled"] is False
    assert body["runner_payload"]["context"]["enabled"] is False


def test_dispatch_force_on_overrides_role_context7_setting() -> None:
    role = client.post("/roles", json={"name": "qa", "context7_enabled": False}).json()
    task = client.post(
        "/tasks",
        json={"role_id": role["id"], "title": "validate library", "context7_mode": "force_on"},
    ).json()

    dispatched = client.post(f"/tasks/{task['id']}/dispatch")
    assert dispatched.status_code == 200
    assert dispatched.json()["resolved_context7_enabled"] is True


def test_task_can_set_explicit_execution_mode() -> None:
    role = client.post("/roles", json={"name": "ops", "context7_enabled": False}).json()
    project = client.post(
        "/projects",
        json={
            "name": "isolated-project",
            "root_path": "/tmp/multyagents/isolated-project",
            "allowed_paths": ["/tmp/multyagents/isolated-project/src"],
        },
    ).json()
    task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "run isolated",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    )
    assert task.status_code == 200
    assert task.json()["execution_mode"] == "isolated-worktree"
    assert task.json()["project_id"] == project["id"]
    assert task.json()["lock_paths"] == []


def test_isolated_worktree_requires_project_id() -> None:
    role = client.post("/roles", json={"name": "isolated-no-project", "context7_enabled": False}).json()
    task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "missing project",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
        },
    )
    assert task.status_code == 422


def test_isolated_worktree_dispatch_contains_worktree_metadata(monkeypatch) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    captured_payload: dict[str, object] = {}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal captured_payload
        captured_payload = kwargs["json"]
        return _FakeResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "isolated-dispatch-role", "context7_enabled": False}).json()
    project = client.post(
        "/projects",
        json={
            "name": "isolated-dispatch-project",
            "root_path": "/tmp/multyagents/isolated-dispatch",
            "allowed_paths": ["/tmp/multyagents/isolated-dispatch/src"],
        },
    ).json()
    task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "isolated dispatch",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    ).json()

    dispatched = client.post(f"/tasks/{task['id']}/dispatch")
    assert dispatched.status_code == 200
    workspace = dispatched.json()["runner_payload"]["workspace"]
    assert workspace["project_id"] == project["id"]
    assert workspace["project_root"] == "/tmp/multyagents/isolated-dispatch"
    assert workspace["worktree_path"].endswith(f"/.multyagents/worktrees/standalone/task-{task['id']}")
    assert workspace["git_branch"] == f"multyagents/standalone/task-{task['id']}"
    assert captured_payload["workspace"]["worktree_path"] == workspace["worktree_path"]
    assert captured_payload["workspace"]["git_branch"] == workspace["git_branch"]
    assert captured_payload["run_id"] == f"task-{task['id']}"

    audit = client.get(f"/tasks/{task['id']}/audit")
    assert audit.status_code == 200
    audit_body = audit.json()
    assert audit_body["workflow_run_id"] is None
    assert audit_body["task_run_id"] == f"standalone:task-{task['id']}"
    assert audit_body["worktree_path"] == workspace["worktree_path"]
    assert audit_body["git_branch"] == workspace["git_branch"]


def test_isolated_worktree_dispatch_uses_workflow_run_in_mapping(monkeypatch) -> None:
    captured_payloads: list[dict[str, object]] = []

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        captured_payloads.append(kwargs["json"])
        return _FakeResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "isolated-run-mapping-role", "context7_enabled": False}).json()
    project = client.post(
        "/projects",
        json={
            "name": "isolated-run-mapping-project",
            "root_path": "/tmp/multyagents/isolated-run-mapping",
            "allowed_paths": ["/tmp/multyagents/isolated-run-mapping/src"],
        },
    ).json()

    first_task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "isolated first",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    ).json()
    second_task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "isolated second",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    ).json()

    run = client.post(
        "/workflow-runs",
        json={"task_ids": [first_task["id"], second_task["id"]], "initiated_by": "isolated-test"},
    )
    assert run.status_code == 200
    run_id = run.json()["id"]

    first_dispatch = client.post(f"/tasks/{first_task['id']}/dispatch")
    assert first_dispatch.status_code == 200
    second_dispatch = client.post(f"/tasks/{second_task['id']}/dispatch")
    assert second_dispatch.status_code == 200

    first_workspace = first_dispatch.json()["runner_payload"]["workspace"]
    second_workspace = second_dispatch.json()["runner_payload"]["workspace"]
    assert first_workspace["worktree_path"] != second_workspace["worktree_path"]
    assert first_workspace["git_branch"] != second_workspace["git_branch"]
    assert f"/run-{run_id}/" in first_workspace["worktree_path"]
    assert f"/run-{run_id}/" in second_workspace["worktree_path"]

    first_audit = client.get(f"/tasks/{first_task['id']}/audit")
    second_audit = client.get(f"/tasks/{second_task['id']}/audit")
    assert first_audit.status_code == 200
    assert second_audit.status_code == 200
    assert first_audit.json()["workflow_run_id"] == run_id
    assert second_audit.json()["workflow_run_id"] == run_id
    assert first_audit.json()["task_run_id"] == f"run-{run_id}:task-{first_task['id']}"
    assert second_audit.json()["task_run_id"] == f"run-{run_id}:task-{second_task['id']}"
    assert captured_payloads[0]["run_id"] == f"run-{run_id}"
    assert captured_payloads[1]["run_id"] == f"run-{run_id}"


def test_isolated_worktree_dispatch_rejects_when_task_already_active(monkeypatch) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _FakeResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "isolated-active-role", "context7_enabled": False}).json()
    project = client.post(
        "/projects",
        json={
            "name": "isolated-active-project",
            "root_path": "/tmp/multyagents/isolated-active",
            "allowed_paths": ["/tmp/multyagents/isolated-active/src"],
        },
    ).json()
    task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "isolated active",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    ).json()

    first_dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert first_dispatch.status_code == 200

    second_dispatch = client.post(f"/tasks/{task['id']}/dispatch")
    assert second_dispatch.status_code == 409
    assert "not dispatchable" in second_dispatch.json()["detail"]


def test_isolated_worktree_collision_is_rejected(monkeypatch) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _FakeResponse()

    def fixed_identifiers(self, *, project_root, task_id, run_id):  # noqa: ANN001, ANN202
        return (
            project_root / ".multyagents" / "worktrees" / "forced-collision",
            "multyagents/forced-collision",
        )

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)
    monkeypatch.setattr(
        store,
        "_build_isolated_session_identifiers",
        MethodType(fixed_identifiers, store),
    )

    role = client.post("/roles", json={"name": "isolated-collision-role", "context7_enabled": False}).json()
    project = client.post(
        "/projects",
        json={
            "name": "isolated-collision-project",
            "root_path": "/tmp/multyagents/isolated-collision",
            "allowed_paths": ["/tmp/multyagents/isolated-collision/src"],
        },
    ).json()

    first_task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "isolated first collision",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    ).json()
    second_task = client.post(
        "/tasks",
        json={
            "role_id": role["id"],
            "title": "isolated second collision",
            "context7_mode": "inherit",
            "execution_mode": "isolated-worktree",
            "project_id": project["id"],
        },
    ).json()

    first_dispatch = client.post(f"/tasks/{first_task['id']}/dispatch")
    assert first_dispatch.status_code == 200

    second_dispatch = client.post(f"/tasks/{second_task['id']}/dispatch")
    assert second_dispatch.status_code == 409
    assert "isolated-worktree collision" in second_dispatch.json()["detail"]


def test_dispatch_reports_runner_submit_success_when_runner_available(monkeypatch) -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        return _FakeResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "runner-role", "context7_enabled": True}).json()
    task = client.post(
        "/tasks",
        json={"role_id": role["id"], "title": "runner task", "context7_mode": "inherit"},
    ).json()

    response = client.post(f"/tasks/{task['id']}/dispatch")
    assert response.status_code == 200
    body = response.json()
    assert body["runner_submission"]["submitted"] is True
    assert body["runner_submission"]["runner_task_status"] == "queued"
    assert body["runner_submission"]["runner_url"] == "http://runner.test"

    monkeypatch.delenv("HOST_RUNNER_URL")


def test_dispatch_includes_runner_callback_fields_when_configured(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        nonlocal captured_payload
        captured_payload = kwargs["json"]
        return _FakeResponse()

    monkeypatch.setenv("HOST_RUNNER_URL", "http://runner.test")
    monkeypatch.setenv("API_RUNNER_CALLBACK_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("API_RUNNER_CALLBACK_TOKEN", "runner-secret")
    monkeypatch.setattr("multyagents_api.runner_client.httpx.post", fake_post)

    role = client.post("/roles", json={"name": "runner-callback-role", "context7_enabled": True}).json()
    task = client.post(
        "/tasks",
        json={"role_id": role["id"], "title": "callback task", "context7_mode": "inherit"},
    ).json()

    response = client.post(f"/tasks/{task['id']}/dispatch")
    assert response.status_code == 200
    assert captured_payload["status_callback_url"] == f"http://localhost:8000/runner/tasks/{task['id']}/status"
    assert captured_payload["status_callback_token"] == "runner-secret"
