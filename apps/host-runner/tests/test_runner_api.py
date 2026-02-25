import threading
import time

from fastapi.testclient import TestClient

from multyagents_host_runner.main import app


client = TestClient(app)


def _wait_for_terminal(task_id: str, timeout_seconds: float = 3.0) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current = client.get(f"/tasks/{task_id}")
        assert current.status_code == 200
        body = current.json()
        if body["status"] in ("success", "failed", "canceled"):
            return body
        time.sleep(0.03)
    raise AssertionError(f"task {task_id} did not reach terminal status in time")


def test_submit_and_get_task() -> None:
    submit = client.post(
        "/tasks/submit",
        json={"task_id": "task-1", "run_id": "run-1", "prompt": "hello"},
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "queued"

    current = client.get("/tasks/task-1")
    assert current.status_code == 200
    assert current.json()["task_id"] == "task-1"


def test_cancel_task() -> None:
    client.post(
        "/tasks/submit",
        json={"task_id": "task-2", "run_id": "run-2", "prompt": "hello"},
    )
    canceled = client.post("/tasks/task-2/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"


def test_mock_execution_reaches_success_with_metadata() -> None:
    submit = client.post(
        "/tasks/submit",
        json={"task_id": "task-5", "run_id": "run-5", "prompt": "hello lifecycle"},
    )
    assert submit.status_code == 200

    terminal = _wait_for_terminal("task-5")
    assert terminal["status"] == "success"
    assert terminal["exit_code"] == 0
    assert terminal["stdout"] == "hello lifecycle"
    assert terminal["executor"] == "mock"
    assert terminal["started_at"] is not None
    assert terminal["finished_at"] is not None


def test_submit_shared_workspace_task() -> None:
    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-3",
            "run_id": "run-3",
            "prompt": "apply changes",
            "execution_mode": "shared-workspace",
            "workspace": {
                "project_id": 1,
                "project_root": "/tmp/multyagents/project",
                "lock_paths": ["/tmp/multyagents/project/src"],
            },
        },
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["execution_mode"] == "shared-workspace"
    assert body["workspace"]["project_id"] == 1


def test_shared_workspace_requires_workspace_payload() -> None:
    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-4",
            "run_id": "run-4",
            "prompt": "apply changes",
            "execution_mode": "shared-workspace",
        },
    )
    assert submit.status_code == 422


def test_runner_sends_status_callbacks(monkeypatch) -> None:
    calls: list[dict] = []

    class _CallbackResponse:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: ANN001
        calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return _CallbackResponse()

    monkeypatch.setattr("multyagents_host_runner.main.httpx.post", fake_post)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-6",
            "run_id": "run-6",
            "prompt": "callback test",
            "status_callback_url": "http://api.local/runner/tasks/6/status",
            "status_callback_token": "callback-token",
        },
    )
    assert submit.status_code == 200
    terminal = _wait_for_terminal("task-6")
    assert terminal["status"] == "success"

    statuses = [call["json"]["status"] for call in calls]
    assert "running" in statuses
    assert "success" in statuses
    assert all(call["headers"].get("X-Runner-Token") == "callback-token" for call in calls)


def test_codex_executor_runs_with_configured_command(monkeypatch) -> None:
    calls: list[dict] = []

    class _Completed:
        returncode = 0
        stdout = "codex ok"
        stderr = ""

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append({"command": command, **kwargs})
        return _Completed()

    monkeypatch.setenv("HOST_RUNNER_EXECUTOR", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_BIN", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_ARGS", "--skip-git-repo-check --sandbox workspace-write")
    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-7",
            "run_id": "run-7",
            "prompt": "Implement feature",
            "execution_mode": "shared-workspace",
            "workspace": {
                "project_id": 1,
                "project_root": "/tmp/multyagents/codex-exec",
                "lock_paths": ["/tmp/multyagents/codex-exec/src"],
            },
        },
    )
    assert submit.status_code == 200
    terminal = _wait_for_terminal("task-7")
    assert terminal["status"] == "success"
    assert terminal["executor"] == "codex"
    assert terminal["stdout"] == "codex ok"

    assert len(calls) == 1
    assert calls[0]["command"] == [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "Implement feature",
    ]
    assert calls[0]["cwd"] == "/tmp/multyagents/codex-exec"


def test_codex_executor_handles_missing_binary(monkeypatch) -> None:
    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        raise FileNotFoundError("codex not found")

    monkeypatch.setenv("HOST_RUNNER_EXECUTOR", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_BIN", "codex")
    monkeypatch.delenv("HOST_RUNNER_CODEX_ARGS", raising=False)
    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={"task_id": "task-8", "run_id": "run-8", "prompt": "Test missing binary"},
    )
    assert submit.status_code == 200
    terminal = _wait_for_terminal("task-8")
    assert terminal["status"] == "failed"
    assert terminal["message"] == "codex binary not found"


def test_isolated_worktree_setup_and_cleanup_with_codex_executor(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _Completed:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        calls.append(command)
        if command[0] == "git" and command[3:5] == ["worktree", "list"]:
            return _Completed(0, stdout="", stderr="")
        if command[0] == "git" and command[3:5] == ["worktree", "add"]:
            return _Completed(0)
        if command[0] == "codex":
            return _Completed(0, stdout="isolated ok", stderr="")
        if command[0] == "git" and command[3:5] == ["worktree", "remove"]:
            return _Completed(0)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setenv("HOST_RUNNER_EXECUTOR", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_BIN", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_ARGS", "--skip-git-repo-check")
    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-9",
            "run_id": "run-9",
            "prompt": "isolated run",
            "execution_mode": "isolated-worktree",
            "workspace": {
                "project_id": 7,
                "project_root": "/tmp/multyagents/isolated-repo",
                "lock_paths": [],
                "worktree_path": "/tmp/multyagents/isolated-repo/.multyagents/worktrees/task-9",
                "git_branch": "multyagents/task-9",
            },
        },
    )
    assert submit.status_code == 200
    terminal = _wait_for_terminal("task-9")
    assert terminal["status"] == "success"
    assert terminal["stdout"] == "isolated ok"

    assert calls[0][0] == "git"
    assert calls[0][3:5] == ["worktree", "list"]
    assert calls[1][0] == "git"
    assert calls[1][3:5] == ["worktree", "add"]
    assert calls[2][0] == "codex"
    assert calls[3][0] == "git"
    assert calls[3][3:5] == ["worktree", "remove"]


def test_isolated_worktree_cleanup_runs_on_failed_execution(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _Completed:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        calls.append(command)
        if command[0] == "git" and command[3:5] == ["worktree", "list"]:
            return _Completed(0, stdout="", stderr="")
        if command[0] == "git" and command[3:5] == ["worktree", "add"]:
            return _Completed(0)
        if command[0] == "codex":
            return _Completed(2, stdout="", stderr="boom")
        if command[0] == "git" and command[3:5] == ["worktree", "remove"]:
            return _Completed(0)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setenv("HOST_RUNNER_EXECUTOR", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_BIN", "codex")
    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-9-failed",
            "run_id": "run-9-failed",
            "prompt": "isolated fail run",
            "execution_mode": "isolated-worktree",
            "workspace": {
                "project_id": 7,
                "project_root": "/tmp/multyagents/isolated-repo",
                "lock_paths": [],
                "worktree_path": "/tmp/multyagents/isolated-repo/.multyagents/worktrees/task-9-failed",
                "git_branch": "multyagents/task-9-failed",
            },
        },
    )
    assert submit.status_code == 200

    terminal = _wait_for_terminal("task-9-failed")
    assert terminal["status"] == "failed"
    assert terminal["worktree_cleanup_attempted"] is True
    assert terminal["worktree_cleanup_succeeded"] is True
    assert any(command[0] == "git" and command[3:5] == ["worktree", "remove"] for command in calls)


def test_isolated_worktree_cleanup_runs_when_canceled(monkeypatch) -> None:
    calls: list[list[str]] = []
    release_executor = threading.Event()

    class _Completed:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        calls.append(command)
        if command[0] == "git" and command[3:5] == ["worktree", "list"]:
            return _Completed(0, stdout="", stderr="")
        if command[0] == "git" and command[3:5] == ["worktree", "add"]:
            return _Completed(0)
        if command[0] == "codex":
            release_executor.wait(timeout=1.0)
            return _Completed(0, stdout="late", stderr="")
        if command[0] == "git" and command[3:5] == ["worktree", "remove"]:
            return _Completed(0)
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setenv("HOST_RUNNER_EXECUTOR", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_BIN", "codex")
    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-9-cancel",
            "run_id": "run-9-cancel",
            "prompt": "isolated cancel run",
            "execution_mode": "isolated-worktree",
            "workspace": {
                "project_id": 7,
                "project_root": "/tmp/multyagents/isolated-repo",
                "lock_paths": [],
                "worktree_path": "/tmp/multyagents/isolated-repo/.multyagents/worktrees/task-9-cancel",
                "git_branch": "multyagents/task-9-cancel",
            },
        },
    )
    assert submit.status_code == 200

    deadline = time.time() + 2.0
    while time.time() < deadline:
        current = client.get("/tasks/task-9-cancel")
        assert current.status_code == 200
        if current.json()["status"] == "running":
            break
        time.sleep(0.03)
    canceled = client.post("/tasks/task-9-cancel/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    release_executor.set()

    time.sleep(0.1)
    assert any(command[0] == "git" and command[3:5] == ["worktree", "remove"] for command in calls)


def test_isolated_worktree_submit_rejects_colliding_branch_and_path(monkeypatch) -> None:
    release_executor = threading.Event()

    class _Completed:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        if command[0] == "git" and command[3:5] == ["worktree", "list"]:
            return _Completed(0, stdout="", stderr="")
        if command[0] == "git" and command[3:5] == ["worktree", "add"]:
            return _Completed(0)
        if command[0] == "git" and command[3:5] == ["worktree", "remove"]:
            return _Completed(0)
        if command[0] == "codex":
            release_executor.wait(timeout=1.0)
            return _Completed(0, stdout="ok", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setenv("HOST_RUNNER_EXECUTOR", "codex")
    monkeypatch.setenv("HOST_RUNNER_CODEX_BIN", "codex")
    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    first_submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-9-collision-a",
            "run_id": "run-9-collision-a",
            "prompt": "collision a",
            "execution_mode": "isolated-worktree",
            "workspace": {
                "project_id": 7,
                "project_root": "/tmp/multyagents/isolated-repo",
                "lock_paths": [],
                "worktree_path": "/tmp/multyagents/isolated-repo/.multyagents/worktrees/collision",
                "git_branch": "multyagents/collision",
            },
        },
    )
    assert first_submit.status_code == 200

    second_submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-9-collision-b",
            "run_id": "run-9-collision-b",
            "prompt": "collision b",
            "execution_mode": "isolated-worktree",
            "workspace": {
                "project_id": 7,
                "project_root": "/tmp/multyagents/isolated-repo",
                "lock_paths": [],
                "worktree_path": "/tmp/multyagents/isolated-repo/.multyagents/worktrees/collision",
                "git_branch": "multyagents/collision",
            },
        },
    )
    assert second_submit.status_code == 409
    assert "isolated-worktree collision" in second_submit.json()["detail"]
    release_executor.set()


def test_isolated_worktree_requires_workspace_metadata() -> None:
    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-10",
            "run_id": "run-10",
            "prompt": "isolated invalid",
            "execution_mode": "isolated-worktree",
            "workspace": {
                "project_id": 1,
                "project_root": "/tmp/multyagents/repo",
            },
        },
    )
    assert submit.status_code == 422


def test_docker_sandbox_execution_runs_docker_command(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _Completed:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        calls.append(command)
        if command[:3] == ["docker", "rm", "-f"]:
            return _Completed(0)
        if command[:2] == ["docker", "run"]:
            return _Completed(0, stdout="sandbox ok", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-11",
            "run_id": "run-11",
            "prompt": "docker task",
            "execution_mode": "docker-sandbox",
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "echo sandbox"],
                "workdir": "/workspace/project",
                "env": {"X": "1"},
                "mounts": [
                    {
                        "source": "/tmp/multyagents/docker-src",
                        "target": "/workspace/project",
                        "read_only": False,
                    }
                ],
            },
        },
    )
    assert submit.status_code == 200

    terminal = _wait_for_terminal("task-11")
    assert terminal["status"] == "success"
    assert terminal["executor"] == "docker-sandbox"
    assert terminal["container_id"] == "multyagents-task-11"
    assert terminal["stdout"] == "sandbox ok"
    run_command = next(cmd for cmd in calls if cmd[:2] == ["docker", "run"])
    assert "--read-only" in run_command
    assert "--cap-drop" in run_command and "ALL" in run_command
    assert "--security-opt" in run_command and "no-new-privileges:true" in run_command
    assert "--network" in run_command and "none" in run_command
    assert "--pids-limit" in run_command and "256" in run_command
    assert "--memory" in run_command and "2g" in run_command
    assert "--cpus" in run_command and "2.0" in run_command


def test_cancel_docker_sandbox_forces_container_stop(monkeypatch) -> None:
    calls: list[list[str]] = []

    class _Completed:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        calls.append(command)
        if command[:3] == ["docker", "rm", "-f"]:
            return _Completed(0)
        if command[:2] == ["docker", "run"]:
            time.sleep(0.25)
            return _Completed(0, stdout="late success", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("multyagents_host_runner.main.subprocess.run", fake_run)

    submit = client.post(
        "/tasks/submit",
        json={
            "task_id": "task-12",
            "run_id": "run-12",
            "prompt": "cancel docker task",
            "execution_mode": "docker-sandbox",
            "sandbox": {
                "image": "alpine:3.20",
                "command": ["sh", "-lc", "sleep 10"],
                "workdir": "/workspace/project",
                "mounts": [
                    {
                        "source": "/tmp/multyagents/docker-cancel",
                        "target": "/workspace/project",
                        "read_only": False,
                    }
                ],
            },
        },
    )
    assert submit.status_code == 200

    deadline = time.time() + 2.0
    while time.time() < deadline:
        current = client.get("/tasks/task-12")
        assert current.status_code == 200
        if current.json()["status"] == "running":
            break
        time.sleep(0.03)
    canceled = client.post("/tasks/task-12/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    assert any(cmd[:3] == ["docker", "rm", "-f"] and cmd[3] == "multyagents-task-12" for cmd in calls)
