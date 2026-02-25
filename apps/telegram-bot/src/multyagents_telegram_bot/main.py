from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="multyagents telegram bot", version="0.1.0")


@dataclass(frozen=True)
class _CommandRoute:
    method: str
    path_template: str
    uses_body: bool = False


_COMMAND_ROUTES: dict[str, _CommandRoute] = {
    "run": _CommandRoute(method="POST", path_template="/workflow-runs", uses_body=True),
    "status": _CommandRoute(method="GET", path_template="/workflow-runs/{id}"),
    "next": _CommandRoute(method="POST", path_template="/workflow-runs/{id}/dispatch-ready"),
    "cancel": _CommandRoute(method="POST", path_template="/tasks/{id}/cancel"),
    "approve": _CommandRoute(method="POST", path_template="/approvals/{id}/approve"),
    "pause": _CommandRoute(method="POST", path_template="/workflow-runs/{id}/pause"),
    "resume": _CommandRoute(method="POST", path_template="/workflow-runs/{id}/resume"),
    "abort": _CommandRoute(method="POST", path_template="/workflow-runs/{id}/abort"),
}


class CommandRequest(BaseModel):
    text: str = Field(min_length=1)
    chat_id: int | str | None = None


class CommandResponse(BaseModel):
    handled: bool
    command: str | None = None
    ok: bool = False
    message: str
    api_method: str | None = None
    api_path: str | None = None
    api_status: int | None = None
    triage_hints: list[str] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config_preview() -> dict[str, str | bool]:
    token_present = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    return {
        "api_base_url": _api_base_url(),
        "token_present": token_present,
    }


@app.get("/telegram/commands")
def list_supported_commands() -> dict[str, list[str]]:
    return {"commands": sorted(_COMMAND_ROUTES.keys())}


@app.post("/telegram/command", response_model=CommandResponse)
def handle_command(payload: CommandRequest) -> CommandResponse:
    return _process_command(payload.text)


@app.post("/telegram/webhook", response_model=CommandResponse)
def telegram_webhook(payload: dict) -> CommandResponse:
    message = payload.get("message") or payload.get("edited_message")
    if not isinstance(message, dict):
        return CommandResponse(
            handled=False,
            message="no message in telegram update",
        )

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        return CommandResponse(
            handled=False,
            message="telegram message has no text command",
        )

    return _process_command(text)


def _process_command(text: str) -> CommandResponse:
    command, args = _parse_command(text)
    if command is None:
        return CommandResponse(
            handled=False,
            message="empty command",
        )

    route = _COMMAND_ROUTES.get(command)
    if route is None:
        return CommandResponse(
            handled=False,
            command=command,
            message="unsupported command. use: run, status, next, cancel, approve, pause, resume, abort",
        )

    if len(args) != 1:
        return CommandResponse(
            handled=True,
            command=command,
            message=f"usage: /{command} <id>",
        )

    target_id = args[0]
    api_path = route.path_template if route.uses_body else route.path_template.format(id=target_id)
    body = {"workflow_template_id": int(target_id)} if route.uses_body and target_id.isdigit() else None

    try:
        response = _call_api(route.method, api_path, body)
        if 200 <= response.status_code < 300:
            message = f"{command} accepted"
            triage_hints: list[str] = []
            if command == "status":
                status_message, hints = _build_status_message(response)
                message = status_message
                triage_hints = hints
            return CommandResponse(
                handled=True,
                command=command,
                ok=True,
                message=message,
                api_method=route.method,
                api_path=api_path,
                api_status=response.status_code,
                triage_hints=triage_hints,
            )
        return CommandResponse(
            handled=True,
            command=command,
            ok=False,
            message=f"api returned {response.status_code}",
            api_method=route.method,
            api_path=api_path,
            api_status=response.status_code,
        )
    except Exception as exc:  # noqa: BLE001
        return CommandResponse(
            handled=True,
            command=command,
            ok=False,
            message=f"api call failed: {exc}",
            api_method=route.method,
            api_path=api_path,
        )


def _api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://api:8000")


def _parse_command(text: str) -> tuple[str | None, list[str]]:
    raw = text.strip()
    if not raw:
        return None, []
    if raw.startswith("/"):
        raw = raw[1:]
    parts = raw.split()
    if not parts:
        return None, []
    return parts[0].lower(), parts[1:]


def _call_api(method: str, path: str, body: dict | None) -> httpx.Response:
    base = _api_base_url().rstrip("/")
    return httpx.request(method=method, url=f"{base}{path}", json=body, timeout=5.0)


def _build_status_message(response: httpx.Response) -> tuple[str, list[str]]:
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return "status accepted", []
    if not isinstance(payload, dict):
        return "status accepted", []

    run_id = payload.get("id")
    run_status = payload.get("status")
    retries = payload.get("retry_summary")
    triage_raw = payload.get("failure_triage_hints")
    triage_hints = [item for item in triage_raw if isinstance(item, str)] if isinstance(triage_raw, list) else []

    retry_total: int | None = None
    if isinstance(retries, dict):
        value = retries.get("total_retries")
        if isinstance(value, int):
            retry_total = value

    label = "run status"
    if run_id is not None and run_status is not None:
        label = f"run {run_id}: {run_status}"
    elif run_status is not None:
        label = f"run: {run_status}"

    if retry_total is not None:
        label = f"{label} (retries={retry_total})"
    if triage_hints:
        label = f"{label}. hint: {triage_hints[0]}"
    return label, triage_hints
