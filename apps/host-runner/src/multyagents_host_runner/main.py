from __future__ import annotations

import os
import re
import shlex
import subprocess
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class RunnerWorkspace(BaseModel):
    project_id: int = Field(ge=1)
    project_root: str = Field(min_length=1)
    lock_paths: list[str] = Field(default_factory=list)
    worktree_path: str | None = Field(default=None, min_length=1)
    git_branch: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_paths(self) -> "RunnerWorkspace":
        root = Path(self.project_root)
        if not root.is_absolute():
            raise ValueError("project_root must be absolute")
        for raw_path in self.lock_paths:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                raise ValueError("lock_paths values must be absolute")
        if self.worktree_path is not None and not Path(self.worktree_path).is_absolute():
            raise ValueError("worktree_path must be absolute")
        return self


class RunnerSandboxMount(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    read_only: bool = False

    @model_validator(mode="after")
    def validate_paths(self) -> "RunnerSandboxMount":
        if not Path(self.source).is_absolute():
            raise ValueError("sandbox mount source must be absolute")
        if not self.target.startswith("/"):
            raise ValueError("sandbox mount target must be absolute")
        return self


class RunnerSandbox(BaseModel):
    image: str = Field(min_length=1)
    command: list[str] = Field(min_length=1)
    workdir: str = Field(default="/workspace/project", min_length=1)
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[RunnerSandboxMount] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_workdir(self) -> "RunnerSandbox":
        if not self.workdir.startswith("/"):
            raise ValueError("sandbox workdir must be absolute")
        return self


class RunnerSubmit(BaseModel):
    task_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    execution_mode: str = Field(default="no-workspace", min_length=1)
    workspace: RunnerWorkspace | None = None
    sandbox: RunnerSandbox | None = None
    status_callback_url: str | None = Field(default=None, min_length=1)
    status_callback_token: str | None = Field(default=None, min_length=1)
    timeout_seconds: int = Field(default=600, ge=1, le=86400)

    @model_validator(mode="after")
    def validate_shared_workspace(self) -> "RunnerSubmit":
        if self.execution_mode == "shared-workspace":
            if self.workspace is None:
                raise ValueError("workspace is required for shared-workspace mode")
            if len(self.workspace.lock_paths) == 0:
                raise ValueError("workspace.lock_paths is required for shared-workspace mode")
        if self.execution_mode == "isolated-worktree":
            if self.workspace is None:
                raise ValueError("workspace is required for isolated-worktree mode")
            if self.workspace.worktree_path is None:
                raise ValueError("workspace.worktree_path is required for isolated-worktree mode")
            if self.workspace.git_branch is None:
                raise ValueError("workspace.git_branch is required for isolated-worktree mode")
        if self.execution_mode == "docker-sandbox" and self.sandbox is None:
            raise ValueError("sandbox is required for docker-sandbox mode")
        if self.status_callback_url is not None and not self.status_callback_url.startswith(("http://", "https://")):
            raise ValueError("status_callback_url must be absolute http(s) url")
        return self


class RunnerTask(BaseModel):
    task_id: str
    run_id: str
    execution_mode: str
    workspace: RunnerWorkspace | None = None
    status: TaskStatus
    message: str
    executor: str
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    container_id: str | None = None


app = FastAPI(title="multyagents host runner", version="0.1.0")
_tasks: dict[str, RunnerTask] = {}
_cancel_flags: set[str] = set()
_task_callbacks: dict[str, tuple[str, str | None]] = {}
_task_lock = threading.Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks/submit", response_model=RunnerTask)
def submit(payload: RunnerSubmit) -> RunnerTask:
    now = _utc_now()
    executor = _resolve_executor(payload)
    task = RunnerTask(
        task_id=payload.task_id,
        run_id=payload.run_id,
        execution_mode=payload.execution_mode,
        workspace=payload.workspace,
        status=TaskStatus.QUEUED,
        message="accepted",
        executor=executor,
        created_at=now,
        updated_at=now,
    )
    with _task_lock:
        _tasks[payload.task_id] = task
        _cancel_flags.discard(payload.task_id)
        if payload.status_callback_url is not None:
            _task_callbacks[payload.task_id] = (payload.status_callback_url, payload.status_callback_token)
        else:
            _task_callbacks.pop(payload.task_id, None)

    _start_execution(payload)
    return task


@app.get("/tasks/{task_id}", response_model=RunnerTask)
def get_task(task_id: str) -> RunnerTask:
    with _task_lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    return task


@app.post("/tasks/{task_id}/cancel", response_model=RunnerTask)
def cancel(task_id: str) -> RunnerTask:
    canceled: RunnerTask | None = None
    with _task_lock:
        task = _tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"task {task_id} not found")

        _cancel_flags.add(task_id)
        if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELED):
            return task

        canceled = task.model_copy(
            update={
                "status": TaskStatus.CANCELED,
                "message": "canceled by api",
                "updated_at": _utc_now(),
                "finished_at": _utc_now(),
            }
        )
        _tasks[task_id] = canceled
        if canceled.execution_mode == "docker-sandbox":
            _stop_docker_container(canceled.container_id)
    if canceled is not None:
        _notify_status(
            task_id,
            status=TaskStatus.CANCELED,
            message=canceled.message,
            finished_at=canceled.finished_at,
            container_id=canceled.container_id,
        )
        with _task_lock:
            _task_callbacks.pop(task_id, None)
        return canceled
    raise HTTPException(status_code=500, detail=f"task {task_id} cancel failed")


def _start_execution(payload: RunnerSubmit) -> None:
    thread = threading.Thread(target=_run_task, args=(payload,), daemon=True)
    thread.start()


def _run_task(payload: RunnerSubmit) -> None:
    container_id: str | None = None
    if payload.execution_mode == "docker-sandbox":
        container_id = _sandbox_container_name(payload.task_id)
    with _task_lock:
        current = _tasks.get(payload.task_id)
        if current is None:
            return
        if current.status == TaskStatus.CANCELED:
            return
        running = current.model_copy(
            update={
                "status": TaskStatus.RUNNING,
                "message": "running",
                "updated_at": _utc_now(),
                "started_at": _utc_now(),
                "container_id": container_id,
            }
        )
        _tasks[payload.task_id] = running
    _notify_status(
        payload.task_id,
        status=TaskStatus.RUNNING,
        message=running.message,
        started_at=running.started_at,
        container_id=running.container_id,
    )
    if _is_canceled(payload.task_id):
        return

    execution_cwd = payload.workspace.project_root if payload.workspace is not None else None
    cleanup_info: tuple[str, str] | None = None

    if payload.execution_mode == "isolated-worktree":
        setup = _setup_isolated_worktree(payload)
        if setup["ok"] is not True:
            result = {
                "status": TaskStatus.FAILED,
                "message": setup["message"],
                "exit_code": setup.get("exit_code"),
                "stdout": setup.get("stdout"),
                "stderr": setup.get("stderr"),
            }
        else:
            execution_cwd = str(setup["cwd"])
            cleanup_info = (payload.workspace.project_root, str(setup["cwd"]))
            executor = _executor_mode()
            if executor == "shell":
                result = _execute_shell(payload, execution_cwd)
            elif executor == "codex":
                result = _execute_codex(payload, execution_cwd)
            else:
                result = _execute_mock(payload)
    elif payload.execution_mode == "docker-sandbox":
        result = _execute_docker_sandbox(payload, container_id=container_id)
    else:
        executor = _executor_mode()
        if executor == "shell":
            result = _execute_shell(payload, execution_cwd)
        elif executor == "codex":
            result = _execute_codex(payload, execution_cwd)
        else:
            result = _execute_mock(payload)

    with _task_lock:
        current = _tasks.get(payload.task_id)
        if current is None:
            return
        if current.status == TaskStatus.CANCELED:
            return

        final = current.model_copy(
            update={
                "status": result["status"],
                "message": result["message"],
                "updated_at": _utc_now(),
                "finished_at": _utc_now(),
                "exit_code": result.get("exit_code"),
                "stdout": result.get("stdout"),
                "stderr": result.get("stderr"),
                "container_id": result.get("container_id", current.container_id),
            }
        )
        _tasks[payload.task_id] = final
    _notify_status(
        payload.task_id,
        status=final.status,
        message=final.message,
        started_at=final.started_at,
        finished_at=final.finished_at,
        exit_code=final.exit_code,
        stdout=final.stdout,
        stderr=final.stderr,
        container_id=final.container_id,
    )
    if cleanup_info is not None:
        _cleanup_isolated_worktree(repo_root=cleanup_info[0], worktree_path=cleanup_info[1])
    with _task_lock:
        _task_callbacks.pop(payload.task_id, None)


def _execute_mock(payload: RunnerSubmit) -> dict[str, object]:
    for _ in range(10):
        if _is_canceled(payload.task_id):
            return {
                "status": TaskStatus.CANCELED,
                "message": "canceled before completion",
                "exit_code": None,
                "stdout": None,
                "stderr": None,
            }
        time.sleep(0.03)

    return {
        "status": TaskStatus.SUCCESS,
        "message": "mock execution completed",
        "exit_code": 0,
        "stdout": payload.prompt,
        "stderr": "",
    }


def _execute_docker_sandbox(payload: RunnerSubmit, *, container_id: str | None) -> dict[str, object]:
    if payload.sandbox is None:
        return {
            "status": TaskStatus.FAILED,
            "message": "docker-sandbox requires sandbox configuration",
            "exit_code": None,
            "stdout": None,
            "stderr": None,
            "container_id": container_id,
        }

    resolved_container = container_id or _sandbox_container_name(payload.task_id)
    _stop_docker_container(resolved_container)
    if _is_canceled(payload.task_id):
        return {
            "status": TaskStatus.CANCELED,
            "message": "canceled before sandbox start",
            "exit_code": None,
            "stdout": None,
            "stderr": None,
            "container_id": resolved_container,
        }

    command: list[str] = [
        "docker",
        "run",
        "--rm",
        "--name",
        resolved_container,
        "-w",
        payload.sandbox.workdir,
    ]
    if _env_bool("HOST_RUNNER_DOCKER_SANDBOX_READ_ONLY_ROOTFS", True):
        command.extend(["--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])
    if _env_bool("HOST_RUNNER_DOCKER_SANDBOX_DROP_CAPS", True):
        command.extend(["--cap-drop", "ALL", "--security-opt", "no-new-privileges:true"])
    network = os.getenv("HOST_RUNNER_DOCKER_SANDBOX_NETWORK", "none").strip() or "none"
    command.extend(["--network", network])
    pids_limit = os.getenv("HOST_RUNNER_DOCKER_SANDBOX_PIDS_LIMIT", "256").strip() or "256"
    memory_limit = os.getenv("HOST_RUNNER_DOCKER_SANDBOX_MEMORY", "2g").strip() or "2g"
    cpus_limit = os.getenv("HOST_RUNNER_DOCKER_SANDBOX_CPUS", "2.0").strip() or "2.0"
    command.extend(["--pids-limit", pids_limit, "--memory", memory_limit, "--cpus", cpus_limit])
    for mount in payload.sandbox.mounts:
        mount_spec = f"{mount.source}:{mount.target}"
        if mount.read_only:
            mount_spec += ":ro"
        command.extend(["-v", mount_spec])
    for key, value in payload.sandbox.env.items():
        command.extend(["-e", f"{key}={value}"])
    command.append(payload.sandbox.image)
    command.extend(payload.sandbox.command)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=payload.timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "status": TaskStatus.FAILED,
            "message": "docker binary not found",
            "exit_code": None,
            "stdout": None,
            "stderr": str(exc),
            "container_id": resolved_container,
        }
    except subprocess.TimeoutExpired as exc:
        _stop_docker_container(resolved_container)
        return {
            "status": TaskStatus.FAILED,
            "message": "docker sandbox execution timed out",
            "exit_code": None,
            "stdout": exc.stdout,
            "stderr": exc.stderr,
            "container_id": resolved_container,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": TaskStatus.FAILED,
            "message": "docker sandbox execution failed",
            "exit_code": None,
            "stdout": None,
            "stderr": str(exc),
            "container_id": resolved_container,
        }

    status = TaskStatus.SUCCESS if completed.returncode == 0 else TaskStatus.FAILED
    return {
        "status": status,
        "message": "docker sandbox execution completed"
        if status == TaskStatus.SUCCESS
        else "docker sandbox execution failed",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "container_id": resolved_container,
    }


def _execute_shell(payload: RunnerSubmit, cwd: str | None) -> dict[str, object]:
    command_template = os.getenv("HOST_RUNNER_CMD_TEMPLATE")
    if not command_template:
        return {
            "status": TaskStatus.FAILED,
            "message": "shell executor requires HOST_RUNNER_CMD_TEMPLATE",
            "exit_code": None,
            "stdout": None,
            "stderr": "missing command template",
        }

    command = command_template.format(
        prompt=payload.prompt,
        task_id=payload.task_id,
        run_id=payload.run_id,
    )
    try:
        completed = subprocess.run(
            ["bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=payload.timeout_seconds,
            cwd=cwd,
            check=False,
        )
        status = TaskStatus.SUCCESS if completed.returncode == 0 else TaskStatus.FAILED
        return {
            "status": status,
            "message": "shell execution completed" if status == TaskStatus.SUCCESS else "shell execution failed",
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": TaskStatus.FAILED,
            "message": "shell execution timed out",
            "exit_code": None,
            "stdout": exc.stdout,
            "stderr": exc.stderr,
        }


def _execute_codex(payload: RunnerSubmit, cwd: str | None) -> dict[str, object]:
    codex_bin = os.getenv("HOST_RUNNER_CODEX_BIN", "codex").strip() or "codex"
    codex_args_raw = os.getenv("HOST_RUNNER_CODEX_ARGS", "")
    codex_args = shlex.split(codex_args_raw) if codex_args_raw.strip() else []
    command = [codex_bin, "exec", *codex_args, payload.prompt]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=payload.timeout_seconds,
            cwd=cwd,
            check=False,
        )
        status = TaskStatus.SUCCESS if completed.returncode == 0 else TaskStatus.FAILED
        return {
            "status": status,
            "message": "codex execution completed" if status == TaskStatus.SUCCESS else "codex execution failed",
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except FileNotFoundError as exc:
        return {
            "status": TaskStatus.FAILED,
            "message": "codex binary not found",
            "exit_code": None,
            "stdout": None,
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": TaskStatus.FAILED,
            "message": "codex execution timed out",
            "exit_code": None,
            "stdout": exc.stdout,
            "stderr": exc.stderr,
        }


def _setup_isolated_worktree(payload: RunnerSubmit) -> dict[str, object]:
    if payload.workspace is None or payload.workspace.worktree_path is None or payload.workspace.git_branch is None:
        return {
            "ok": False,
            "message": "isolated-worktree setup requires workspace.worktree_path and workspace.git_branch",
            "exit_code": None,
            "stdout": None,
            "stderr": None,
        }

    repo_root = payload.workspace.project_root
    worktree_path = payload.workspace.worktree_path
    git_branch = payload.workspace.git_branch
    Path(worktree_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                repo_root,
                "worktree",
                "add",
                "--force",
                "-B",
                git_branch,
                worktree_path,
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "message": "isolated worktree setup failed",
            "exit_code": None,
            "stdout": None,
            "stderr": str(exc),
        }

    if completed.returncode != 0:
        return {
            "ok": False,
            "message": "isolated worktree setup failed",
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    return {
        "ok": True,
        "cwd": Path(worktree_path),
    }


def _cleanup_isolated_worktree(*, repo_root: str, worktree_path: str) -> None:
    cleanup_enabled = os.getenv("HOST_RUNNER_CLEANUP_WORKTREE", "true").lower() != "false"
    if not cleanup_enabled:
        return

    try:
        subprocess.run(
            [
                "git",
                "-C",
                repo_root,
                "worktree",
                "remove",
                "--force",
                worktree_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return


def _executor_mode() -> str:
    return os.getenv("HOST_RUNNER_EXECUTOR", "mock")


def _resolve_executor(payload: RunnerSubmit) -> str:
    if payload.execution_mode == "docker-sandbox":
        return "docker-sandbox"
    return _executor_mode()


def _sandbox_container_name(task_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", task_id).strip("-")
    if not normalized:
        normalized = "task"
    return f"multyagents-{normalized}"


def _stop_docker_container(container_id: str | None) -> None:
    if not container_id:
        return
    try:
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception:  # noqa: BLE001
        return


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _is_canceled(task_id: str) -> bool:
    with _task_lock:
        return task_id in _cancel_flags


def _notify_status(
    task_id: str,
    *,
    status: TaskStatus,
    message: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    container_id: str | None = None,
) -> None:
    with _task_lock:
        callback = _task_callbacks.get(task_id)
    if callback is None:
        return

    url, token = callback
    payload: dict[str, object | None] = {
        "status": status.value,
        "message": message,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "container_id": container_id,
    }
    headers: dict[str, str] = {}
    if token:
        headers["X-Runner-Token"] = token
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=5.0)
        response.raise_for_status()
    except Exception:  # noqa: BLE001
        return


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
