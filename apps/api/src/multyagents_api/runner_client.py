from __future__ import annotations

import os

import httpx

from multyagents_api.security import redact_sensitive_text
from multyagents_api.schemas import RunnerSubmission, RunnerSubmitPayload


def _runner_url() -> str | None:
    return os.getenv("HOST_RUNNER_URL") or os.getenv("API_HOST_RUNNER_URL")


def _runner_callback_base_url() -> str | None:
    return os.getenv("API_RUNNER_CALLBACK_BASE_URL") or os.getenv("API_PUBLIC_BASE_URL")


def submit_to_runner(payload: RunnerSubmitPayload) -> RunnerSubmission:
    base_url = _runner_url()
    if not base_url:
        return RunnerSubmission(
            submitted=False,
            runner_url=None,
            message="runner url not configured",
        )

    request_payload = {
        "task_id": str(payload.task_id),
        "run_id": f"run-{payload.run_id}" if payload.run_id is not None else f"task-{payload.task_id}",
        "prompt": payload.title,
        "execution_mode": payload.execution_mode.value,
        "timeout_seconds": 600,
    }
    callback_base = _runner_callback_base_url()
    if callback_base:
        request_payload["status_callback_url"] = (
            f"{callback_base.rstrip('/')}/runner/tasks/{payload.task_id}/status"
        )
    callback_token = os.getenv("API_RUNNER_CALLBACK_TOKEN")
    if callback_token:
        request_payload["status_callback_token"] = callback_token
    if payload.workspace is not None:
        request_payload["workspace"] = {
            "project_id": payload.workspace.project_id,
            "project_root": payload.workspace.project_root,
            "lock_paths": payload.workspace.lock_paths,
        }
        if payload.workspace.worktree_path is not None:
            request_payload["workspace"]["worktree_path"] = payload.workspace.worktree_path
        if payload.workspace.git_branch is not None:
            request_payload["workspace"]["git_branch"] = payload.workspace.git_branch
    if payload.sandbox is not None:
        request_payload["sandbox"] = payload.sandbox.model_dump()
    if payload.handoff_context:
        request_payload["handoff_context"] = [item.model_dump() for item in payload.handoff_context]

    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/tasks/submit",
            json=request_payload,
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
        return RunnerSubmission(
            submitted=True,
            runner_url=base_url,
            runner_task_status=data.get("status"),
            message="submitted",
        )
    except Exception as exc:  # noqa: BLE001
        sanitized_error = redact_sensitive_text(str(exc))
        return RunnerSubmission(
            submitted=False,
            runner_url=base_url,
            message=f"runner submit failed: {sanitized_error}",
        )


def cancel_in_runner(task_id: int) -> RunnerSubmission:
    base_url = _runner_url()
    if not base_url:
        return RunnerSubmission(
            submitted=False,
            runner_url=None,
            message="runner url not configured",
        )

    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/tasks/{task_id}/cancel",
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
        return RunnerSubmission(
            submitted=True,
            runner_url=base_url,
            runner_task_status=data.get("status"),
            message="cancel requested",
        )
    except Exception as exc:  # noqa: BLE001
        sanitized_error = redact_sensitive_text(str(exc))
        return RunnerSubmission(
            submitted=False,
            runner_url=base_url,
            message=f"runner cancel failed: {sanitized_error}",
        )
