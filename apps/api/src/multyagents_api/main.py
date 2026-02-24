from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from multyagents_api.runner_client import cancel_in_runner, submit_to_runner
from multyagents_api.schemas import (
    ApprovalDecisionRequest,
    ApprovalRead,
    ArtifactCreate,
    ArtifactRead,
    ArtifactType,
    ContractVersion,
    DispatchResponse,
    EventCreate,
    EventRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    RoleCreate,
    RoleRead,
    RunnerStatusUpdate,
    RoleUpdate,
    TaskAudit,
    TaskCreate,
    TaskLocksReleaseResponse,
    TaskRead,
    WorkflowRunCreate,
    WorkflowRunDispatchReadyResponse,
    WorkflowRunRead,
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
    WorkflowTemplateUpdate,
)
from multyagents_api.store import ConflictError, InMemoryStore, NotFoundError, ValidationError

app = FastAPI(title="multyagents api", version="0.1.0")
store = InMemoryStore(state_file=os.getenv("API_STATE_FILE"))
CONTRACT_VERSION = "v1"
CONTRACT_SCHEMA_FILE = "packages/contracts/v1/context7.schema.json"


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    trimmed = value.strip()
    return trimmed if trimmed else default


def _parse_csv_env(name: str, default: str = "") -> list[str]:
    value = _env_or_default(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


cors_allow_origins = _parse_csv_env("API_CORS_ALLOW_ORIGINS", default="null")
cors_allow_origin_regex = _env_or_default(
    "API_CORS_ALLOW_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/contracts/current", response_model=ContractVersion)
def get_contract_version() -> ContractVersion:
    return ContractVersion(contract_version=CONTRACT_VERSION, schema_file=CONTRACT_SCHEMA_FILE)


@app.post("/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate) -> ProjectRead:
    return store.create_project(payload)


@app.get("/projects", response_model=list[ProjectRead])
def list_projects() -> list[ProjectRead]:
    return store.list_projects()


@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int) -> ProjectRead:
    try:
        return store.get_project(project_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/projects/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate) -> ProjectRead:
    try:
        return store.update_project(project_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int) -> None:
    try:
        store.delete_project(project_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/roles", response_model=RoleRead)
def create_role(payload: RoleCreate) -> RoleRead:
    return store.create_role(payload)


@app.get("/roles", response_model=list[RoleRead])
def list_roles() -> list[RoleRead]:
    return store.list_roles()


@app.get("/roles/{role_id}", response_model=RoleRead)
def get_role(role_id: int) -> RoleRead:
    try:
        return store.get_role(role_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/roles/{role_id}", response_model=RoleRead)
def update_role(role_id: int, payload: RoleUpdate) -> RoleRead:
    try:
        return store.update_role(
            role_id,
            name=payload.name,
            context7_enabled=payload.context7_enabled,
            system_prompt=payload.system_prompt,
            allowed_tools=payload.allowed_tools,
            skill_packs=payload.skill_packs,
            execution_constraints=payload.execution_constraints,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: int) -> None:
    try:
        store.delete_role(role_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/workflow-templates", response_model=WorkflowTemplateRead)
def create_workflow_template(payload: WorkflowTemplateCreate) -> WorkflowTemplateRead:
    try:
        return store.create_workflow_template(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/workflow-templates", response_model=list[WorkflowTemplateRead])
def list_workflow_templates() -> list[WorkflowTemplateRead]:
    return store.list_workflow_templates()


@app.get("/workflow-templates/{workflow_template_id}", response_model=WorkflowTemplateRead)
def get_workflow_template(workflow_template_id: int) -> WorkflowTemplateRead:
    try:
        return store.get_workflow_template(workflow_template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/workflow-templates/{workflow_template_id}", response_model=WorkflowTemplateRead)
def update_workflow_template(workflow_template_id: int, payload: WorkflowTemplateUpdate) -> WorkflowTemplateRead:
    try:
        return store.update_workflow_template(workflow_template_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/workflow-templates/{workflow_template_id}", status_code=204)
def delete_workflow_template(workflow_template_id: int) -> None:
    try:
        store.delete_workflow_template(workflow_template_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/workflow-runs", response_model=WorkflowRunRead)
def create_workflow_run(payload: WorkflowRunCreate) -> WorkflowRunRead:
    try:
        return store.create_workflow_run(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/workflow-runs", response_model=list[WorkflowRunRead])
def list_workflow_runs() -> list[WorkflowRunRead]:
    return store.list_workflow_runs()


@app.get("/workflow-runs/{run_id}", response_model=WorkflowRunRead)
def get_workflow_run(run_id: int) -> WorkflowRunRead:
    try:
        return store.get_workflow_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/workflow-runs/{run_id}/pause", response_model=WorkflowRunRead)
def pause_workflow_run(run_id: int) -> WorkflowRunRead:
    try:
        return store.pause_workflow_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/workflow-runs/{run_id}/resume", response_model=WorkflowRunRead)
def resume_workflow_run(run_id: int) -> WorkflowRunRead:
    try:
        return store.resume_workflow_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/workflow-runs/{run_id}/abort", response_model=WorkflowRunRead)
def abort_workflow_run(run_id: int) -> WorkflowRunRead:
    try:
        run = store.abort_workflow_run(run_id)
        for task_id in run.task_ids:
            cancel_result = cancel_in_runner(task_id)
            store.apply_runner_cancel_request(task_id, cancel_result)
        return run
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/workflow-runs/{run_id}/dispatch-ready", response_model=WorkflowRunDispatchReadyResponse)
def dispatch_ready_workflow_run(run_id: int) -> WorkflowRunDispatchReadyResponse:
    try:
        task_id, reason = store.next_dispatchable_task_id(run_id)
        if task_id is None:
            return WorkflowRunDispatchReadyResponse(
                run_id=run_id,
                dispatched=False,
                reason=reason,
            )

        dispatch_result = store.dispatch_task(task_id)
        runner_submission = submit_to_runner(dispatch_result.runner_payload)
        store.apply_runner_submission(task_id, runner_submission)
        dispatch_response = DispatchResponse(
            task_id=dispatch_result.task_id,
            resolved_context7_enabled=dispatch_result.resolved_context7_enabled,
            runner_payload=dispatch_result.runner_payload,
            runner_submission=runner_submission,
        )
        return WorkflowRunDispatchReadyResponse(
            run_id=run_id,
            dispatched=True,
            task_id=task_id,
            dispatch=dispatch_response,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/events", response_model=list[EventRead])
def list_events(
    run_id: int | None = None,
    task_id: int | None = None,
    event_type: str | None = None,
    limit: int = 200,
) -> list[EventRead]:
    return store.list_events(run_id=run_id, task_id=task_id, event_type=event_type, limit=limit)


@app.post("/events", response_model=EventRead)
def create_event(payload: EventCreate) -> EventRead:
    try:
        return store.create_event(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    run_id: int | None = None,
    task_id: int | None = None,
    artifact_type: ArtifactType | None = None,
    limit: int = 200,
) -> list[ArtifactRead]:
    return store.list_artifacts(run_id=run_id, task_id=task_id, artifact_type=artifact_type, limit=limit)


@app.post("/artifacts", response_model=ArtifactRead)
def create_artifact(payload: ArtifactCreate) -> ArtifactRead:
    try:
        return store.create_artifact(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/tasks", response_model=TaskRead)
def create_task(payload: TaskCreate) -> TaskRead:
    try:
        return store.create_task(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(run_id: int | None = None) -> list[TaskRead]:
    try:
        return store.list_tasks(run_id=run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int) -> TaskRead:
    try:
        return store.get_task(task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/tasks/{task_id}/dispatch", response_model=DispatchResponse)
def dispatch_task(task_id: int) -> DispatchResponse:
    try:
        dispatch_result = store.dispatch_task(task_id)
        runner_submission = submit_to_runner(dispatch_result.runner_payload)
        store.apply_runner_submission(task_id, runner_submission)
        return DispatchResponse(
            task_id=dispatch_result.task_id,
            resolved_context7_enabled=dispatch_result.resolved_context7_enabled,
            runner_payload=dispatch_result.runner_payload,
            runner_submission=runner_submission,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/runner/tasks/{task_id}/status", response_model=TaskRead)
def update_runner_status(
    task_id: int,
    payload: RunnerStatusUpdate,
    x_runner_token: str | None = Header(default=None),
) -> TaskRead:
    _require_runner_token(x_runner_token)
    try:
        return store.update_task_runner_status(
            task_id,
            status=payload.status,
            message=payload.message,
            started_at=payload.started_at,
            finished_at=payload.finished_at,
            exit_code=payload.exit_code,
            stdout=payload.stdout,
            stderr=payload.stderr,
            container_id=payload.container_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/tasks/{task_id}/cancel", response_model=TaskRead)
def cancel_task(task_id: int) -> TaskRead:
    try:
        cancel_result = cancel_in_runner(task_id)
        return store.apply_runner_cancel_request(task_id, cancel_result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/tasks/{task_id}/locks/release", response_model=TaskLocksReleaseResponse)
def release_task_locks(task_id: int) -> TaskLocksReleaseResponse:
    try:
        released = store.release_task_locks(task_id)
        return TaskLocksReleaseResponse(task_id=task_id, released_paths=released)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tasks/{task_id}/approval", response_model=ApprovalRead)
def get_task_approval(task_id: int) -> ApprovalRead:
    try:
        return store.get_task_approval(task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/approvals/{approval_id}", response_model=ApprovalRead)
def get_approval(approval_id: int) -> ApprovalRead:
    try:
        return store.get_approval(approval_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/approve", response_model=ApprovalRead)
def approve_approval(approval_id: int, payload: ApprovalDecisionRequest | None = None) -> ApprovalRead:
    try:
        actor = payload.actor if payload is not None else None
        comment = payload.comment if payload is not None else None
        return store.approve_approval(approval_id, actor=actor, comment=comment)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/reject", response_model=ApprovalRead)
def reject_approval(approval_id: int, payload: ApprovalDecisionRequest | None = None) -> ApprovalRead:
    try:
        actor = payload.actor if payload is not None else None
        comment = payload.comment if payload is not None else None
        return store.reject_approval(approval_id, actor=actor, comment=comment)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tasks/{task_id}/audit", response_model=TaskAudit)
def get_task_audit(task_id: int) -> TaskAudit:
    try:
        return store.get_task_audit(task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _require_runner_token(token: str | None) -> None:
    expected = os.getenv("API_RUNNER_CALLBACK_TOKEN")
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="invalid runner token")
