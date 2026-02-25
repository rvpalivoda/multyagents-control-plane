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


class QualityGateSeverity(str, Enum):
    BLOCKER = "blocker"
    WARN = "warn"


class QualityGateCheckId(str, Enum):
    TASK_STATUS = "task-status"
    APPROVAL_STATUS = "approval-status"
    HANDOFF_PRESENT = "handoff-present"
    REQUIRED_ARTIFACTS_PRESENT = "required-artifacts-present"


class QualityGateCheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    SKIPPED = "skipped"


class QualityGateSummaryStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    NOT_CONFIGURED = "not-configured"


class QualityGateCheckPolicy(BaseModel):
    check: QualityGateCheckId | str = QualityGateCheckId.TASK_STATUS
    required: bool = True
    severity: QualityGateSeverity = QualityGateSeverity.BLOCKER
    config: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None

    @model_validator(mode="after")
    def normalize_fields(self) -> "QualityGateCheckPolicy":
        if isinstance(self.check, str):
            self.check = self.check.strip()
            if not self.check:
                raise ValueError("quality gate check must not be empty")
        if self.description is not None:
            trimmed = self.description.strip()
            self.description = trimmed if trimmed else None
        return self


class QualityGatePolicy(BaseModel):
    required_checks: list[QualityGateCheckPolicy] = Field(default_factory=list)


class QualityGateCheckResult(BaseModel):
    check: str
    status: QualityGateCheckStatus
    severity: QualityGateSeverity
    required: bool = True
    blocker: bool = False
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class QualityGateSummary(BaseModel):
    status: QualityGateSummaryStatus = QualityGateSummaryStatus.NOT_CONFIGURED
    summary_text: str = "No quality gates configured."
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    pending_checks: int = 0
    skipped_checks: int = 0
    blocker_failures: int = 0
    warning_failures: int = 0
    checks: list[QualityGateCheckResult] = Field(default_factory=list)


class QualityGateRunSummary(BaseModel):
    status: QualityGateSummaryStatus = QualityGateSummaryStatus.NOT_CONFIGURED
    summary_text: str = "No quality gates evaluated for this run yet."
    total_tasks: int = 0
    passing_tasks: int = 0
    failing_tasks: int = 0
    pending_tasks: int = 0
    not_configured_tasks: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    pending_checks: int = 0
    skipped_checks: int = 0
    blocker_failures: int = 0
    warning_failures: int = 0


def _default_task_quality_gate_policy() -> QualityGatePolicy:
    return QualityGatePolicy(
        required_checks=[
            QualityGateCheckPolicy(
                check=QualityGateCheckId.TASK_STATUS,
                required=True,
                severity=QualityGateSeverity.BLOCKER,
            )
        ]
    )


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
    quality_gate_policy: QualityGatePolicy = Field(default_factory=_default_task_quality_gate_policy)

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
    failure_category: str | None = None
    failure_triage_hints: list[str] = Field(default_factory=list)
    suggested_next_actions: list[str] = Field(default_factory=list)
    quality_gate_policy: QualityGatePolicy = Field(default_factory=QualityGatePolicy)
    quality_gate_summary: QualityGateSummary = Field(default_factory=QualityGateSummary)


class RunnerContext(BaseModel):
    provider: str = "context7"
    enabled: bool


class RunnerWorkspaceContext(BaseModel):
    project_id: int
    project_root: str
    lock_paths: list[str] = Field(default_factory=list)
    worktree_path: str | None = None
    git_branch: str | None = None


class TaskHandoffArtifactRef(BaseModel):
    artifact_id: int = Field(ge=1)
    is_required: bool = False
    note: str | None = None


class TaskHandoffPayload(BaseModel):
    summary: str = Field(min_length=1)
    details: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    artifacts: list[TaskHandoffArtifactRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_text_fields(self) -> "TaskHandoffPayload":
        self.summary = self.summary.strip()
        if self.details is not None:
            trimmed_details = self.details.strip()
            self.details = trimmed_details if trimmed_details else None
        self.next_actions = _normalize_string_list(self.next_actions)
        self.open_questions = _normalize_string_list(self.open_questions)
        return self


class TaskHandoffRead(TaskHandoffPayload):
    task_id: int
    run_id: int | None = None
    created_at: str
    updated_at: str


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
    handoff_context: list[TaskHandoffRead] = Field(default_factory=list)


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
    handoff: TaskHandoffPayload | None = None


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
    handoff: TaskHandoffRead | None = None
    consumed_artifact_ids: list[int] = Field(default_factory=list)
    produced_artifact_ids: list[int] = Field(default_factory=list)
    retry_attempts: int = 0
    last_retry_reason: str | None = None
    failure_categories: list[str] = Field(default_factory=list)
    failure_triage_hints: list[str] = Field(default_factory=list)
    rerun_count: int = 0
    last_rerun_by: str | None = None
    last_rerun_reason: str | None = None
    last_rerun_at: str | None = None
    recent_event_ids: list[int] = Field(default_factory=list)


class WorkflowRunStepTaskOverride(BaseModel):
    context7_mode: Context7Mode = Context7Mode.INHERIT
    execution_mode: ExecutionMode = ExecutionMode.NO_WORKSPACE
    requires_approval: bool = False
    project_id: int | None = None
    lock_paths: list[str] = Field(default_factory=list)
    sandbox: SandboxConfig | None = None

    @model_validator(mode="after")
    def validate_workspace_fields(self) -> "WorkflowRunStepTaskOverride":
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


class WorkflowRunCreate(BaseModel):
    workflow_template_id: int | None = None
    task_ids: list[int] = Field(default_factory=list)
    initiated_by: str | None = None
    step_task_overrides: dict[str, WorkflowRunStepTaskOverride] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_inputs(self) -> "WorkflowRunCreate":
        if self.workflow_template_id is None and not self.task_ids:
            raise ValueError("workflow_template_id or task_ids is required")
        if self.step_task_overrides and self.workflow_template_id is None:
            raise ValueError("step_task_overrides requires workflow_template_id")
        if self.step_task_overrides and self.task_ids:
            raise ValueError("step_task_overrides is supported only when task_ids is empty")
        self.step_task_overrides = _normalize_step_override_map(self.step_task_overrides)
        return self


class WorkflowRunRoleMetric(BaseModel):
    role_id: int
    task_count: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    throughput_tasks: int = 0
    success_rate: float = 0.0
    retries_total: int = 0
    duration_ms: int | None = None


class WorkflowRunRead(BaseModel):
    id: int
    workflow_template_id: int | None = None
    task_ids: list[int] = Field(default_factory=list)
    status: WorkflowRunStatus
    initiated_by: str | None = None
    created_at: str
    updated_at: str
    retry_summary: dict[str, Any] = Field(default_factory=dict)
    failure_categories: list[str] = Field(default_factory=list)
    failure_triage_hints: list[str] = Field(default_factory=list)
    suggested_next_actions: list[str] = Field(default_factory=list)
    duration_ms: int | None = None
    success_rate: float = 0.0
    retries_total: int = 0
    per_role: list[WorkflowRunRoleMetric] = Field(default_factory=list)
    quality_gate_summary: QualityGateRunSummary = Field(default_factory=QualityGateRunSummary)


class WorkflowRunDispatchReadyResponse(BaseModel):
    run_id: int
    dispatched: bool
    task_id: int | None = None
    reason: str | None = None
    dispatch: DispatchResponse | None = None


class WorkflowRunControlLoopRequest(BaseModel):
    max_dispatch: int = Field(default=10, ge=1, le=100)


class WorkflowRunDispatchPlanItem(BaseModel):
    task_id: int
    consumed_artifact_ids: list[int] = Field(default_factory=list)


class WorkflowRunDispatchBlockedItem(BaseModel):
    task_id: int | None = None
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunDispatchPlan(BaseModel):
    ready: list[WorkflowRunDispatchPlanItem] = Field(default_factory=list)
    blocked: list[WorkflowRunDispatchBlockedItem] = Field(default_factory=list)


class WorkflowRunSpawnResult(BaseModel):
    task_id: int
    submitted: bool = False
    task_status: TaskStatus
    dispatch: DispatchResponse | None = None
    error: str | None = None


class WorkflowRunExecutionTaskSummary(BaseModel):
    task_id: int
    title: str
    role_id: int
    status: TaskStatus
    runner_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    requires_approval: bool = False
    approval_status: ApprovalStatus | None = None
    consumed_artifact_ids: list[int] = Field(default_factory=list)
    produced_artifact_ids: list[int] = Field(default_factory=list)
    handoff_summary: str | None = None
    quality_gate_summary: QualityGateSummary = Field(default_factory=QualityGateSummary)


class WorkflowRunTimelineEntry(BaseModel):
    task_id: int
    branch: str
    owner_role_id: int
    stage_id: str
    stage: str
    stage_state: str
    progress_percent: float = 0.0
    blocked_reasons: list[str] = Field(default_factory=list)


class WorkflowRunExecutionSummary(BaseModel):
    run: WorkflowRunRead
    task_status_counts: dict[str, int] = Field(default_factory=dict)
    terminal: bool = False
    partial_completion: bool = False
    progress_percent: float = 0.0
    branch_status_cards: dict[str, int] = Field(default_factory=dict)
    next_dispatch: WorkflowRunDispatchPlan = Field(default_factory=WorkflowRunDispatchPlan)
    successful_task_ids: list[int] = Field(default_factory=list)
    failed_task_ids: list[int] = Field(default_factory=list)
    active_task_ids: list[int] = Field(default_factory=list)
    pending_task_ids: list[int] = Field(default_factory=list)
    timeline: list[WorkflowRunTimelineEntry] = Field(default_factory=list)
    tasks: list[WorkflowRunExecutionTaskSummary] = Field(default_factory=list)


class WorkflowRunControlLoopResponse(BaseModel):
    run_id: int
    plan: WorkflowRunDispatchPlan
    spawn: list[WorkflowRunSpawnResult] = Field(default_factory=list)
    aggregate: WorkflowRunExecutionSummary


class WorkflowRunPartialRerunRequest(BaseModel):
    task_ids: list[int] = Field(default_factory=list)
    step_ids: list[str] = Field(default_factory=list)
    requested_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    auto_dispatch: bool = True
    max_dispatch: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def normalize_fields(self) -> "WorkflowRunPartialRerunRequest":
        deduplicated_task_ids: list[int] = []
        for task_id in self.task_ids:
            if task_id <= 0:
                raise ValueError("task_ids must contain positive integers")
            if task_id in deduplicated_task_ids:
                continue
            deduplicated_task_ids.append(task_id)
        self.task_ids = deduplicated_task_ids

        deduplicated_step_ids: list[str] = []
        for step_id in self.step_ids:
            trimmed = step_id.strip()
            if not trimmed:
                continue
            if trimmed in deduplicated_step_ids:
                continue
            deduplicated_step_ids.append(trimmed)
        self.step_ids = deduplicated_step_ids

        self.requested_by = self.requested_by.strip()
        self.reason = self.reason.strip()
        if not self.requested_by:
            raise ValueError("requested_by must not be empty")
        if not self.reason:
            raise ValueError("reason must not be empty")
        if not self.task_ids and not self.step_ids:
            raise ValueError("task_ids or step_ids is required")
        return self


class WorkflowRunPartialRerunResponse(BaseModel):
    run_id: int
    requested_by: str
    reason: str
    selected_task_ids: list[int] = Field(default_factory=list)
    selected_step_ids: list[str] = Field(default_factory=list)
    reset_task_ids: list[int] = Field(default_factory=list)
    plan: WorkflowRunDispatchPlan = Field(default_factory=WorkflowRunDispatchPlan)
    spawn: list[WorkflowRunSpawnResult] = Field(default_factory=list)
    aggregate: WorkflowRunExecutionSummary


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
    quality_gate_policy: QualityGatePolicy = Field(default_factory=_default_task_quality_gate_policy)

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


class AssistantIntentPlanRequest(BaseModel):
    workflow_template_id: int
    initiated_by: str | None = "assistant"
    step_task_overrides: dict[str, WorkflowRunStepTaskOverride] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_inputs(self) -> "AssistantIntentPlanRequest":
        self.step_task_overrides = _normalize_step_override_map(self.step_task_overrides)
        return self


class AssistantIntentStartRequest(AssistantIntentPlanRequest):
    dispatch_ready: bool = True


class AssistantPlanStepRead(BaseModel):
    step_id: str
    role_id: int
    title: str
    depends_on: list[str] = Field(default_factory=list)
    required_artifacts: list[WorkflowArtifactRequirement] = Field(default_factory=list)
    quality_gate_policy: QualityGatePolicy = Field(default_factory=_default_task_quality_gate_policy)
    task_config: WorkflowRunStepTaskOverride


class AssistantMachineSummary(BaseModel):
    contract_version: str = "v1"
    phase: str = Field(min_length=1)
    run_id: int | None = None
    workflow_template_id: int | None = None
    workflow_status: WorkflowRunStatus | None = None
    total_tasks: int = 0
    task_status_counts: dict[str, int] = Field(default_factory=dict)
    ready_task_ids: list[int] = Field(default_factory=list)
    blocked_by_approval_task_ids: list[int] = Field(default_factory=list)
    terminal_task_ids: list[int] = Field(default_factory=list)
    failed_task_ids: list[int] = Field(default_factory=list)
    produced_artifact_ids: list[int] = Field(default_factory=list)
    handoff_task_ids: list[int] = Field(default_factory=list)
    planned_step_ids: list[str] = Field(default_factory=list)
    planned_approval_step_ids: list[str] = Field(default_factory=list)
    recent_event_types: list[str] = Field(default_factory=list)


class AssistantIntentPlanResponse(BaseModel):
    workflow_template_id: int
    initiated_by: str | None = None
    steps: list[AssistantPlanStepRead] = Field(default_factory=list)
    machine_summary: AssistantMachineSummary


class AssistantIntentStartResponse(BaseModel):
    run: WorkflowRunRead
    steps: list[AssistantPlanStepRead] = Field(default_factory=list)
    dispatches: list[DispatchResponse] = Field(default_factory=list)
    blocked_by_approval_task_ids: list[int] = Field(default_factory=list)
    machine_summary: AssistantMachineSummary


class AssistantIntentStatusRequest(BaseModel):
    run_id: int
    include_tasks: bool = True


class AssistantIntentStatusResponse(BaseModel):
    run: WorkflowRunRead
    tasks: list[TaskRead] = Field(default_factory=list)
    machine_summary: AssistantMachineSummary


class AssistantIntentReportRequest(BaseModel):
    run_id: int
    event_limit: int = Field(default=200, ge=1, le=1000)
    artifact_limit: int = Field(default=200, ge=1, le=1000)
    handoff_limit: int = Field(default=200, ge=1, le=1000)


class AssistantIntentReportResponse(BaseModel):
    run: WorkflowRunRead
    tasks: list[TaskRead] = Field(default_factory=list)
    events: list[EventRead] = Field(default_factory=list)
    artifacts: list[ArtifactRead] = Field(default_factory=list)
    handoffs: list[TaskHandoffRead] = Field(default_factory=list)
    machine_summary: AssistantMachineSummary


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


def _normalize_step_override_map(
    values: dict[str, WorkflowRunStepTaskOverride],
) -> dict[str, WorkflowRunStepTaskOverride]:
    normalized: dict[str, WorkflowRunStepTaskOverride] = {}
    for step_id, override in values.items():
        trimmed = step_id.strip()
        if not trimmed:
            raise ValueError("step_task_overrides keys must be non-empty")
        if trimmed in normalized:
            raise ValueError(f"duplicate step_task_overrides key: {trimmed}")
        normalized[trimmed] = override
    return normalized
