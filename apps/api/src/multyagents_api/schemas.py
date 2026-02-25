from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator
from multyagents_api.workflow_validation import validate_workflow_dag


class Context7Mode(str, Enum):
    INHERIT = "inherit"
    FORCE_ON = "force_on"
    FORCE_OFF = "force_off"


class ExecutionMode(str, Enum):
    NO_WORKSPACE = "no-workspace"
    SHARED_WORKSPACE = "shared-workspace"
    ISOLATED_WORKTREE = "isolated-worktree"
    DOCKER_SANDBOX = "docker-sandbox"


class TaskStatus(str, Enum):
    CREATED = "created"
    DISPATCHED = "dispatched"
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel-requested"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"
    SUBMIT_FAILED = "submit-failed"


class ArtifactType(str, Enum):
    TEXT = "text"
    FILE = "file"
    DIFF = "diff"
    COMMIT = "commit"
    REPORT = "report"
    CUSTOM = "custom"


class RunnerLifecycleStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowRunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    ABORTED = "aborted"
    SUCCESS = "success"
    FAILED = "failed"


class RoleCreate(BaseModel):
    name: str = Field(min_length=1)
    context7_enabled: bool = False
    system_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    skill_packs: list[str] = Field(default_factory=list)
    execution_constraints: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_fields(self) -> "RoleCreate":
        self.allowed_tools = _normalize_string_list(self.allowed_tools)
        self.skill_packs = _normalize_string_list(self.skill_packs)
        return self


class RoleRead(BaseModel):
    id: int
    name: str
    context7_enabled: bool
    system_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    skill_packs: list[str] = Field(default_factory=list)
    execution_constraints: dict[str, Any] = Field(default_factory=dict)


class RoleUpdate(BaseModel):
    name: str = Field(min_length=1)
    context7_enabled: bool
    system_prompt: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    skill_packs: list[str] = Field(default_factory=list)
    execution_constraints: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_fields(self) -> "RoleUpdate":
        self.allowed_tools = _normalize_string_list(self.allowed_tools)
        self.skill_packs = _normalize_string_list(self.skill_packs)
        return self


class SkillPackCreate(BaseModel):
    name: str = Field(min_length=1)
    skills: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_fields(self) -> "SkillPackCreate":
        self.name = self.name.strip()
        self.skills = _normalize_string_list(self.skills)
        return self


class SkillPackRead(BaseModel):
    id: int
    name: str
    skills: list[str] = Field(default_factory=list)
    used_by_role_ids: list[int] = Field(default_factory=list)


class SkillPackUpdate(SkillPackCreate):
    pass


class TaskCreate(BaseModel):
    role_id: int
    title: str = Field(min_length=1)
    context7_mode: Context7Mode = Context7Mode.INHERIT
    execution_mode: ExecutionMode = ExecutionMode.NO_WORKSPACE
    requires_approval: bool = False
    project_id: int | None = None
    lock_paths: list[str] = Field(default_factory=list)
    sandbox: SandboxConfig | None = None

    @model_validator(mode="after")
    def validate_workspace_fields(self) -> "TaskCreate":
        normalized_lock_paths: list[str] = []
        for raw_path in self.lock_paths:
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                raise ValueError("lock_paths values must be absolute paths")
            normalized_lock_paths.append(str(candidate.resolve()))

        if self.execution_mode == ExecutionMode.SHARED_WORKSPACE:
            if self.project_id is None:
                raise ValueError("project_id is required for shared-workspace mode")
            if not normalized_lock_paths:
                raise ValueError("lock_paths is required for shared-workspace mode")
        if self.execution_mode == ExecutionMode.ISOLATED_WORKTREE:
            if self.project_id is None:
                raise ValueError("project_id is required for isolated-worktree mode")
        if self.execution_mode == ExecutionMode.DOCKER_SANDBOX:
            if self.project_id is None:
                raise ValueError("project_id is required for docker-sandbox mode")
            if self.sandbox is None:
                raise ValueError("sandbox is required for docker-sandbox mode")
        if self.execution_mode != ExecutionMode.DOCKER_SANDBOX and self.sandbox is not None:
            raise ValueError("sandbox is supported only for docker-sandbox mode")

        self.lock_paths = normalized_lock_paths
        return self


class TaskRead(BaseModel):
    id: int
    role_id: int
    title: str
    context7_mode: Context7Mode
    execution_mode: ExecutionMode
    status: TaskStatus = TaskStatus.CREATED
    requires_approval: bool = False
    project_id: int | None = None
    lock_paths: list[str] = Field(default_factory=list)
    sandbox: SandboxConfig | None = None
    runner_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None


class RunnerContext(BaseModel):
    provider: str = "context7"
    enabled: bool


class RunnerWorkspaceContext(BaseModel):
    project_id: int
    project_root: str
    lock_paths: list[str] = Field(default_factory=list)
    worktree_path: str | None = None
    git_branch: str | None = None


class SandboxMount(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    read_only: bool = False

    @model_validator(mode="after")
    def validate_paths(self) -> "SandboxMount":
        source_path = Path(self.source)
        target_path = Path(self.target)
        if not source_path.is_absolute():
            raise ValueError("sandbox mount source must be absolute path")
        if not target_path.is_absolute():
            raise ValueError("sandbox mount target must be absolute path")
        self.source = str(source_path.resolve())
        self.target = str(target_path)
        return self


class SandboxConfig(BaseModel):
    image: str = Field(min_length=1)
    command: list[str] = Field(min_length=1)
    workdir: str = Field(default="/workspace/project", min_length=1)
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[SandboxMount] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_workdir(self) -> "SandboxConfig":
        if not self.workdir.startswith("/"):
            raise ValueError("sandbox workdir must be absolute path")
        return self


class RunnerSubmitPayload(BaseModel):
    task_id: int
    run_id: int | None = None
    role_id: int
    title: str
    execution_mode: ExecutionMode
    role_skill_packs: list[str] = Field(default_factory=list)
    context: RunnerContext
    workspace: RunnerWorkspaceContext | None = None
    sandbox: SandboxConfig | None = None


class RunnerSubmission(BaseModel):
    submitted: bool
    runner_url: str | None = None
    runner_task_status: str | None = None
    message: str | None = None


class DispatchResponse(BaseModel):
    task_id: int
    resolved_context7_enabled: bool
    runner_payload: RunnerSubmitPayload
    runner_submission: RunnerSubmission | None = None


class TaskLocksReleaseResponse(BaseModel):
    task_id: int
    released_paths: list[str]


class ApprovalRead(BaseModel):
    id: int
    task_id: int
    status: ApprovalStatus
    decided_by: str | None = None
    comment: str | None = None


class ApprovalDecisionRequest(BaseModel):
    actor: str | None = None
    comment: str | None = None


class RunnerStatusUpdate(BaseModel):
    status: RunnerLifecycleStatus
    message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    container_id: str | None = None
    worktree_cleanup_attempted: bool | None = None
    worktree_cleanup_succeeded: bool | None = None
    worktree_cleanup_message: str | None = None


class TaskAudit(BaseModel):
    task_id: int
    role_id: int
    context7_mode: Context7Mode
    role_context7_enabled: bool
    resolved_context7_enabled: bool
    execution_mode: ExecutionMode
    requires_approval: bool = False
    approval_status: ApprovalStatus | None = None
    workflow_run_id: int | None = None
    task_run_id: str | None = None
    project_id: int | None = None
    lock_paths: list[str] = Field(default_factory=list)
    worktree_path: str | None = None
    git_branch: str | None = None
    worktree_cleanup_attempted: bool = False
    worktree_cleanup_succeeded: bool | None = None
    worktree_cleanup_message: str | None = None
    worktree_cleanup_at: str | None = None
    sandbox_image: str | None = None
    sandbox_workdir: str | None = None
    sandbox_container_id: str | None = None
    sandbox_exit_code: int | None = None
    sandbox_error: str | None = None
    consumed_artifact_ids: list[int] = Field(default_factory=list)
    produced_artifact_ids: list[int] = Field(default_factory=list)
    recent_event_ids: list[int] = Field(default_factory=list)


class WorkflowRunCreate(BaseModel):
    workflow_template_id: int | None = None
    task_ids: list[int] = Field(default_factory=list)
    initiated_by: str | None = None

    @model_validator(mode="after")
    def validate_inputs(self) -> "WorkflowRunCreate":
        if self.workflow_template_id is None and not self.task_ids:
            raise ValueError("workflow_template_id or task_ids is required")
        return self


class WorkflowRunRead(BaseModel):
    id: int
    workflow_template_id: int | None = None
    task_ids: list[int] = Field(default_factory=list)
    status: WorkflowRunStatus
    initiated_by: str | None = None
    created_at: str
    updated_at: str


class WorkflowRunDispatchReadyResponse(BaseModel):
    run_id: int
    dispatched: bool
    task_id: int | None = None
    reason: str | None = None
    dispatch: DispatchResponse | None = None


class EventCreate(BaseModel):
    contract_version: str = "v1"
    event_type: str = Field(min_length=1)
    run_id: int | None = None
    task_id: int | None = None
    producer_role: str = Field(default="system", min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_linkage(self) -> "EventCreate":
        if self.contract_version != "v1":
            raise ValueError("unsupported contract_version")
        if self.run_id is None and self.task_id is None:
            raise ValueError("run_id or task_id is required")
        return self


class EventRead(BaseModel):
    id: int
    contract_version: str = "v1"
    event_type: str
    run_id: int | None = None
    task_id: int | None = None
    producer_role: str = "system"
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ArtifactCreate(BaseModel):
    contract_version: str = "v1"
    artifact_type: ArtifactType
    location: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    producer_task_id: int
    run_id: int | None = None
    task_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_linkage(self) -> "ArtifactCreate":
        if self.contract_version != "v1":
            raise ValueError("unsupported contract_version")
        if self.task_id is None:
            self.task_id = self.producer_task_id
        return self


class ArtifactRead(BaseModel):
    id: int
    contract_version: str = "v1"
    artifact_type: ArtifactType
    location: str
    summary: str
    producer_task_id: int
    run_id: int | None = None
    task_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ContractVersion(BaseModel):
    contract_version: str
    schema_file: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    root_path: str = Field(min_length=1)
    allowed_paths: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_paths(self) -> "ProjectCreate":
        root = Path(self.root_path)
        if not root.is_absolute():
            raise ValueError("root_path must be an absolute path")

        normalized_root = root.resolve()
        normalized_allowed: list[str] = []
        for allowed_path in self.allowed_paths:
            candidate = Path(allowed_path)
            if not candidate.is_absolute():
                raise ValueError("allowed_paths values must be absolute paths")
            normalized_candidate = candidate.resolve()
            if normalized_candidate != normalized_root and normalized_root not in normalized_candidate.parents:
                raise ValueError("allowed_paths values must be under root_path")
            normalized_allowed.append(str(normalized_candidate))

        self.root_path = str(normalized_root)
        self.allowed_paths = normalized_allowed
        return self


class ProjectRead(BaseModel):
    id: int
    name: str
    root_path: str
    allowed_paths: list[str]


class ProjectUpdate(ProjectCreate):
    pass


class WorkflowStep(BaseModel):
    step_id: str = Field(min_length=1)
    role_id: int
    title: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    required_artifacts: list["WorkflowArtifactRequirement"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_artifacts(self) -> "WorkflowStep":
        for requirement in self.required_artifacts:
            if requirement.from_step_id is not None and requirement.from_step_id not in self.depends_on:
                raise ValueError("workflow required_artifacts.from_step_id must reference depends_on step")
        return self


class WorkflowArtifactRequirement(BaseModel):
    from_step_id: str | None = None
    artifact_type: ArtifactType | None = None
    label: str | None = None


class WorkflowTemplateCreate(BaseModel):
    name: str = Field(min_length=1)
    project_id: int | None = None
    steps: list[WorkflowStep] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dag(self) -> "WorkflowTemplateCreate":
        validate_workflow_dag(self.steps)
        return self


class WorkflowTemplateUpdate(WorkflowTemplateCreate):
    pass


class WorkflowTemplateRead(BaseModel):
    id: int
    name: str
    project_id: int | None = None
    steps: list[WorkflowStep]


def _normalize_string_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        trimmed = value.strip()
        if not trimmed:
            continue
        if trimmed in normalized:
            continue
        normalized.append(trimmed)
    return normalized
