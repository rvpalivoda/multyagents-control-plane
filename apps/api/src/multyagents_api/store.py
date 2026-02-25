from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from multyagents_api.context_policy import resolve_context7_enabled
from multyagents_api.schemas import (
    AssistantIntentPlanRequest,
    AssistantIntentPlanResponse,
    AssistantIntentReportRequest,
    AssistantIntentReportResponse,
    AssistantIntentStartRequest,
    AssistantIntentStartResponse,
    AssistantIntentStatusRequest,
    AssistantIntentStatusResponse,
    AssistantMachineSummary,
    AssistantPlanStepRead,
    ApprovalRead,
    ApprovalStatus,
    ArtifactCreate,
    ArtifactRead,
    ArtifactType,
    Context7Mode,
    DispatchResponse,
    EventCreate,
    EventRead,
    ExecutionMode,
    QualityGateCheckId,
    QualityGateCheckResult,
    QualityGateCheckStatus,
    QualityGatePolicy,
    QualityGateRunSummary,
    QualityGateSeverity,
    QualityGateSummary,
    QualityGateSummaryStatus,
    ProjectCreate,
    ProjectRead,
    RunnerLifecycleStatus,
    RunnerSubmission,
    SkillPackCreate,
    SkillPackRead,
    SkillPackUpdate,
    RoleCreate,
    RoleRead,
    RunnerContext,
    SandboxConfig,
    SandboxMount,
    RunnerWorkspaceContext,
    RunnerSubmitPayload,
    TaskAudit,
    TaskHandoffPayload,
    TaskHandoffRead,
    TaskCreate,
    TaskRead,
    TaskStatus,
    WorkflowRunCreate,
    WorkflowRunDispatchBlockedItem,
    WorkflowRunDispatchPlan,
    WorkflowRunDispatchPlanItem,
    WorkflowRunExecutionSummary,
    WorkflowRunExecutionTaskSummary,
    WorkflowRunRead,
    WorkflowRunRoleMetric,
    WorkflowRunStepTaskOverride,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
)


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ValidationError(Exception):
    pass


@dataclass
class _RoleRecord:
    id: int
    name: str
    context7_enabled: bool
    system_prompt: str
    allowed_tools: list[str]
    skill_packs: list[str]
    execution_constraints: dict[str, Any]


@dataclass
class _SkillPackRecord:
    id: int
    name: str
    skills: list[str]


@dataclass
class _TaskRecord:
    id: int
    role_id: int
    title: str
    context7_mode: str
    execution_mode: str
    requires_approval: bool
    project_id: int | None
    lock_paths: list[str]
    sandbox: dict[str, Any] | None = None
    quality_gate_policy: dict[str, Any] = field(default_factory=dict)
    status: str = TaskStatus.CREATED.value
    runner_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None


@dataclass
class _ProjectRecord:
    id: int
    name: str
    root_path: str
    allowed_paths: list[str]


@dataclass
class _WorkflowTemplateRecord:
    id: int
    name: str
    project_id: int | None
    steps: list[WorkflowStep]


@dataclass
class _WorkflowRunRecord:
    id: int
    workflow_template_id: int | None
    task_ids: list[int]
    status: str
    initiated_by: str | None
    created_at: str
    updated_at: str
    step_dependencies: dict[int, list[int]] = field(default_factory=dict)
    step_artifact_requirements: dict[int, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass
class _ApprovalRecord:
    id: int
    task_id: int
    status: str
    decided_by: str | None
    comment: str | None


@dataclass
class _IsolatedSessionRecord:
    task_id: int
    run_id: int | None
    task_run_id: str
    project_id: int
    project_root: str
    worktree_path: str
    git_branch: str


class InMemoryStore:
    def __init__(self, state_file: str | None = None) -> None:
        self._state_file = Path(state_file).expanduser() if state_file else None
        self._skills_catalog = self._load_skills_catalog()
        self._projects: dict[int, _ProjectRecord] = {}
        self._skill_packs: dict[int, _SkillPackRecord] = {}
        self._roles: dict[int, _RoleRecord] = {}
        self._tasks: dict[int, _TaskRecord] = {}
        self._path_locks: dict[str, int] = {}
        self._task_locks: dict[int, list[str]] = {}
        self._workflow_templates: dict[int, _WorkflowTemplateRecord] = {}
        self._workflow_runs: dict[int, _WorkflowRunRecord] = {}
        self._task_latest_run: dict[int, int] = {}
        self._approvals: dict[int, _ApprovalRecord] = {}
        self._task_approval: dict[int, int] = {}
        self._isolated_sessions: dict[int, _IsolatedSessionRecord] = {}
        self._isolated_worktree_locks: dict[str, int] = {}
        self._isolated_branch_locks: dict[str, int] = {}
        self._audits: dict[int, TaskAudit] = {}
        self._handoffs: dict[int, TaskHandoffRead] = {}
        self._events: list[EventRead] = []
        self._artifacts: list[ArtifactRead] = []
        self._project_seq = 1
        self._skill_pack_seq = 1
        self._role_seq = 1
        self._task_seq = 1
        self._workflow_template_seq = 1
        self._workflow_run_seq = 1
        self._approval_seq = 1
        self._event_seq = 1
        self._artifact_seq = 1
        self._load_state()

    def create_skill_pack(self, pack: SkillPackCreate) -> SkillPackRead:
        self._validate_skill_pack(name=pack.name, skills=pack.skills)
        if any(record.name == pack.name for record in self._skill_packs.values()):
            raise ConflictError(f"skill pack '{pack.name}' already exists")

        pack_id = self._skill_pack_seq
        self._skill_pack_seq += 1
        record = _SkillPackRecord(id=pack_id, name=pack.name, skills=pack.skills)
        self._skill_packs[pack_id] = record
        self._persist_state()
        return self._to_skill_pack_read(record)

    def list_skill_packs(self) -> list[SkillPackRead]:
        return [self._to_skill_pack_read(record) for record in self._skill_packs.values()]

    def get_skill_pack(self, pack_id: int) -> SkillPackRead:
        record = self._skill_packs.get(pack_id)
        if record is None:
            raise NotFoundError(f"skill pack {pack_id} not found")
        return self._to_skill_pack_read(record)

    def update_skill_pack(self, pack_id: int, pack: SkillPackUpdate) -> SkillPackRead:
        if pack_id not in self._skill_packs:
            raise NotFoundError(f"skill pack {pack_id} not found")
        self._validate_skill_pack(name=pack.name, skills=pack.skills)
        if any(record.id != pack_id and record.name == pack.name for record in self._skill_packs.values()):
            raise ConflictError(f"skill pack '{pack.name}' already exists")

        updated = _SkillPackRecord(id=pack_id, name=pack.name, skills=pack.skills)
        self._skill_packs[pack_id] = updated
        self._persist_state()
        return self._to_skill_pack_read(updated)

    def delete_skill_pack(self, pack_id: int) -> None:
        record = self._skill_packs.get(pack_id)
        if record is None:
            raise NotFoundError(f"skill pack {pack_id} not found")
        for role in self._roles.values():
            if record.name in role.skill_packs:
                raise ConflictError(f"skill pack '{record.name}' is used by role {role.id}")
        del self._skill_packs[pack_id]
        self._persist_state()

    def create_project(self, project: ProjectCreate) -> ProjectRead:
        project_id = self._project_seq
        self._project_seq += 1
        record = _ProjectRecord(
            id=project_id,
            name=project.name,
            root_path=project.root_path,
            allowed_paths=project.allowed_paths,
        )
        self._projects[project_id] = record
        self._persist_state()
        return ProjectRead(
            id=record.id,
            name=record.name,
            root_path=record.root_path,
            allowed_paths=record.allowed_paths,
        )

    def list_projects(self) -> list[ProjectRead]:
        return [
            ProjectRead(
                id=record.id,
                name=record.name,
                root_path=record.root_path,
                allowed_paths=record.allowed_paths,
            )
            for record in self._projects.values()
        ]

    def get_project(self, project_id: int) -> ProjectRead:
        record = self._projects.get(project_id)
        if record is None:
            raise NotFoundError(f"project {project_id} not found")
        return ProjectRead(
            id=record.id,
            name=record.name,
            root_path=record.root_path,
            allowed_paths=record.allowed_paths,
        )

    def update_project(self, project_id: int, project: ProjectCreate) -> ProjectRead:
        if project_id not in self._projects:
            raise NotFoundError(f"project {project_id} not found")

        updated = _ProjectRecord(
            id=project_id,
            name=project.name,
            root_path=project.root_path,
            allowed_paths=project.allowed_paths,
        )
        self._projects[project_id] = updated
        self._persist_state()
        return ProjectRead(
            id=updated.id,
            name=updated.name,
            root_path=updated.root_path,
            allowed_paths=updated.allowed_paths,
        )

    def delete_project(self, project_id: int) -> None:
        if project_id not in self._projects:
            raise NotFoundError(f"project {project_id} not found")
        for workflow in self._workflow_templates.values():
            if workflow.project_id == project_id:
                raise ConflictError(f"project {project_id} has linked workflow templates")
        for task in self._tasks.values():
            if task.project_id == project_id:
                raise ConflictError(f"project {project_id} has linked tasks")
        del self._projects[project_id]
        self._persist_state()

    def create_workflow_template(self, workflow: WorkflowTemplateCreate) -> WorkflowTemplateRead:
        if workflow.project_id is not None and workflow.project_id not in self._projects:
            raise NotFoundError(f"project {workflow.project_id} not found")
        for step in workflow.steps:
            if step.role_id not in self._roles:
                raise NotFoundError(f"role {step.role_id} not found")

        workflow_id = self._workflow_template_seq
        self._workflow_template_seq += 1
        record = _WorkflowTemplateRecord(
            id=workflow_id,
            name=workflow.name,
            project_id=workflow.project_id,
            steps=workflow.steps,
        )
        self._workflow_templates[workflow_id] = record
        self._persist_state()
        return WorkflowTemplateRead(
            id=record.id,
            name=record.name,
            project_id=record.project_id,
            steps=record.steps,
        )

    def list_workflow_templates(self) -> list[WorkflowTemplateRead]:
        return [
            WorkflowTemplateRead(
                id=record.id,
                name=record.name,
                project_id=record.project_id,
                steps=record.steps,
            )
            for record in self._workflow_templates.values()
        ]

    def get_workflow_template(self, workflow_template_id: int) -> WorkflowTemplateRead:
        record = self._workflow_templates.get(workflow_template_id)
        if record is None:
            raise NotFoundError(f"workflow template {workflow_template_id} not found")
        return WorkflowTemplateRead(
            id=record.id,
            name=record.name,
            project_id=record.project_id,
            steps=record.steps,
        )

    def update_workflow_template(self, workflow_template_id: int, workflow: WorkflowTemplateCreate) -> WorkflowTemplateRead:
        if workflow_template_id not in self._workflow_templates:
            raise NotFoundError(f"workflow template {workflow_template_id} not found")
        if workflow.project_id is not None and workflow.project_id not in self._projects:
            raise NotFoundError(f"project {workflow.project_id} not found")
        for step in workflow.steps:
            if step.role_id not in self._roles:
                raise NotFoundError(f"role {step.role_id} not found")

        updated = _WorkflowTemplateRecord(
            id=workflow_template_id,
            name=workflow.name,
            project_id=workflow.project_id,
            steps=workflow.steps,
        )
        self._workflow_templates[workflow_template_id] = updated
        self._persist_state()
        return WorkflowTemplateRead(
            id=updated.id,
            name=updated.name,
            project_id=updated.project_id,
            steps=updated.steps,
        )

    def delete_workflow_template(self, workflow_template_id: int) -> None:
        if workflow_template_id not in self._workflow_templates:
            raise NotFoundError(f"workflow template {workflow_template_id} not found")
        del self._workflow_templates[workflow_template_id]
        self._persist_state()

    def create_workflow_run(self, run: WorkflowRunCreate) -> WorkflowRunRead:
        if run.workflow_template_id is not None and run.workflow_template_id not in self._workflow_templates:
            raise NotFoundError(f"workflow template {run.workflow_template_id} not found")
        for task_id in run.task_ids:
            if task_id not in self._tasks:
                raise NotFoundError(f"task {task_id} not found")

        resolved_task_ids = list(run.task_ids)
        step_dependencies: dict[int, list[int]] = {}
        step_artifact_requirements: dict[int, list[dict[str, Any]]] = {}
        if run.workflow_template_id is not None and not resolved_task_ids:
            template = self._workflow_templates[run.workflow_template_id]
            known_step_ids = {step.step_id for step in template.steps}
            unknown_override_step_ids = sorted(set(run.step_task_overrides) - known_step_ids)
            if unknown_override_step_ids:
                unknown_joined = ", ".join(unknown_override_step_ids)
                raise ValidationError(f"unknown workflow step overrides: {unknown_joined}")
            step_to_task_id: dict[str, int] = {}
            for step in template.steps:
                override = self._resolve_step_task_override(
                    template_project_id=template.project_id,
                    override=run.step_task_overrides.get(step.step_id),
                )
                created = self.create_task(
                    TaskCreate(
                        role_id=step.role_id,
                        title=step.title,
                        context7_mode=override.context7_mode,
                        execution_mode=override.execution_mode,
                        requires_approval=override.requires_approval,
                        project_id=override.project_id,
                        lock_paths=override.lock_paths,
                        sandbox=override.sandbox,
                        quality_gate_policy=step.quality_gate_policy,
                    )
                )
                step_to_task_id[step.step_id] = created.id

            for step in template.steps:
                task_id = step_to_task_id[step.step_id]
                dependencies = [step_to_task_id[dep] for dep in step.depends_on]
                step_dependencies[task_id] = dependencies
                mapped_requirements: list[dict[str, Any]] = []
                for requirement in step.required_artifacts:
                    from_task_ids: list[int]
                    if requirement.from_step_id is not None:
                        from_task_ids = [step_to_task_id[requirement.from_step_id]]
                    else:
                        from_task_ids = [step_to_task_id[dep] for dep in step.depends_on]
                    mapped_requirements.append(
                        {
                            "from_task_ids": from_task_ids,
                            "artifact_type": requirement.artifact_type.value
                            if requirement.artifact_type is not None
                            else None,
                            "label": requirement.label,
                        }
                    )
                step_artifact_requirements[task_id] = mapped_requirements

            resolved_task_ids = [step_to_task_id[step.step_id] for step in template.steps]

        now = self._utc_now()
        run_id = self._workflow_run_seq
        self._workflow_run_seq += 1
        record = _WorkflowRunRecord(
            id=run_id,
            workflow_template_id=run.workflow_template_id,
            task_ids=resolved_task_ids,
            status=WorkflowRunStatus.CREATED.value,
            initiated_by=run.initiated_by,
            created_at=now,
            updated_at=now,
            step_dependencies=step_dependencies,
            step_artifact_requirements=step_artifact_requirements,
        )
        self._workflow_runs[run_id] = record

        for task_id in resolved_task_ids:
            self._task_latest_run[task_id] = run_id

        self._append_event(
            event_type="workflow_run.created",
            run_id=run_id,
            payload={
                "workflow_template_id": run.workflow_template_id,
                "task_ids": resolved_task_ids,
                "initiated_by": run.initiated_by,
            },
        )
        self._persist_state()
        return self._to_workflow_run_read(record)

    def list_workflow_runs(self) -> list[WorkflowRunRead]:
        return [self._to_workflow_run_read(record) for record in self._workflow_runs.values()]

    def get_workflow_run(self, run_id: int) -> WorkflowRunRead:
        record = self._workflow_runs.get(run_id)
        if record is None:
            raise NotFoundError(f"workflow run {run_id} not found")
        return self._to_workflow_run_read(record)

    def plan_assistant_intent(self, payload: AssistantIntentPlanRequest) -> AssistantIntentPlanResponse:
        template = self._workflow_templates.get(payload.workflow_template_id)
        if template is None:
            raise NotFoundError(f"workflow template {payload.workflow_template_id} not found")

        steps = self._assistant_plan_steps(template, payload.step_task_overrides)
        planned_step_ids = [step.step_id for step in steps]
        planned_approval_step_ids = [step.step_id for step in steps if step.task_config.requires_approval]
        summary = AssistantMachineSummary(
            phase="plan",
            workflow_template_id=template.id,
            total_tasks=len(steps),
            task_status_counts={"planned": len(steps)} if steps else {},
            planned_step_ids=planned_step_ids,
            planned_approval_step_ids=planned_approval_step_ids,
        )
        return AssistantIntentPlanResponse(
            workflow_template_id=template.id,
            initiated_by=payload.initiated_by,
            steps=steps,
            machine_summary=summary,
        )

    def start_assistant_intent(
        self,
        payload: AssistantIntentStartRequest,
        *,
        submitter: Callable[[RunnerSubmitPayload], RunnerSubmission],
    ) -> AssistantIntentStartResponse:
        plan = self.plan_assistant_intent(
            AssistantIntentPlanRequest(
                workflow_template_id=payload.workflow_template_id,
                initiated_by=payload.initiated_by,
                step_task_overrides=payload.step_task_overrides,
            )
        )
        run = self.create_workflow_run(
            WorkflowRunCreate(
                workflow_template_id=payload.workflow_template_id,
                initiated_by=payload.initiated_by,
                step_task_overrides=payload.step_task_overrides,
            )
        )

        dispatches: list[DispatchResponse] = []
        blocked_by_approval_task_ids: list[int] = []
        if payload.dispatch_ready:
            dispatch_candidates, blocked_by_approval_task_ids = self._assistant_dispatch_candidates(run.id)
            for task_id in blocked_by_approval_task_ids:
                approval_status = self._approval_status_for_task(task_id)
                approval_id = self._task_approval.get(task_id)
                self._append_event(
                    event_type="task.dispatch_blocked_by_approval",
                    run_id=run.id,
                    task_id=task_id,
                    payload={
                        "approval_id": approval_id,
                        "status": approval_status.value if approval_status is not None else None,
                    },
                )

            for task_id, consumed_artifact_ids in dispatch_candidates:
                dispatch_result = self.dispatch_task(task_id, consumed_artifact_ids=consumed_artifact_ids)
                runner_submission = submitter(dispatch_result.runner_payload)
                self.apply_runner_submission(task_id, runner_submission)
                dispatches.append(
                    DispatchResponse(
                        task_id=dispatch_result.task_id,
                        resolved_context7_enabled=dispatch_result.resolved_context7_enabled,
                        runner_payload=dispatch_result.runner_payload,
                        runner_submission=runner_submission,
                    )
                )

            if blocked_by_approval_task_ids and not dispatch_candidates:
                self._persist_state()

        machine_summary = self._build_assistant_machine_summary(run_id=run.id, phase="start")
        return AssistantIntentStartResponse(
            run=self.get_workflow_run(run.id),
            steps=plan.steps,
            dispatches=dispatches,
            blocked_by_approval_task_ids=blocked_by_approval_task_ids,
            machine_summary=machine_summary,
        )

    def status_assistant_intent(self, payload: AssistantIntentStatusRequest) -> AssistantIntentStatusResponse:
        run = self.get_workflow_run(payload.run_id)
        tasks = self.list_tasks(run_id=payload.run_id) if payload.include_tasks else []
        machine_summary = self._build_assistant_machine_summary(run_id=payload.run_id, phase="status")
        return AssistantIntentStatusResponse(
            run=run,
            tasks=tasks,
            machine_summary=machine_summary,
        )

    def report_assistant_intent(self, payload: AssistantIntentReportRequest) -> AssistantIntentReportResponse:
        run = self.get_workflow_run(payload.run_id)
        tasks = self.list_tasks(run_id=payload.run_id)
        events = self.list_events(run_id=payload.run_id, limit=payload.event_limit)
        artifacts = self.list_artifacts(run_id=payload.run_id, limit=payload.artifact_limit)
        handoffs = self.list_handoffs(run_id=payload.run_id, limit=payload.handoff_limit)
        machine_summary = self._build_assistant_machine_summary(
            run_id=payload.run_id,
            phase="report",
            preloaded_events=events,
            preloaded_artifacts=artifacts,
            preloaded_handoffs=handoffs,
        )
        return AssistantIntentReportResponse(
            run=run,
            tasks=tasks,
            events=events,
            artifacts=artifacts,
            handoffs=handoffs,
            machine_summary=machine_summary,
        )

    def pause_workflow_run(self, run_id: int) -> WorkflowRunRead:
        return self._set_workflow_run_status(run_id, WorkflowRunStatus.PAUSED, "workflow_run.paused")

    def resume_workflow_run(self, run_id: int) -> WorkflowRunRead:
        return self._set_workflow_run_status(run_id, WorkflowRunStatus.RUNNING, "workflow_run.resumed")

    def abort_workflow_run(self, run_id: int) -> WorkflowRunRead:
        return self._set_workflow_run_status(run_id, WorkflowRunStatus.ABORTED, "workflow_run.aborted")

    def next_dispatchable_task_id(self, run_id: int) -> tuple[int | None, str | None, list[int]]:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")

        if run.status == WorkflowRunStatus.ABORTED.value:
            raise ConflictError(f"workflow run {run_id} is aborted")
        if run.status == WorkflowRunStatus.PAUSED.value:
            raise ConflictError(f"workflow run {run_id} is paused")

        dependency_blocked = False
        artifact_blocked = False
        blocked_task_id: int | None = None
        blocked_requirements: list[dict[str, Any]] = []
        for task_id in run.task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status not in (TaskStatus.CREATED.value, TaskStatus.SUBMIT_FAILED.value):
                continue

            dependencies = run.step_dependencies.get(task_id, [])
            if all(
                self._tasks.get(dep_task_id) is not None
                and self._tasks[dep_task_id].status == TaskStatus.SUCCESS.value
                for dep_task_id in dependencies
            ):
                consumed_artifact_ids, missing_requirements = self._resolve_handoff_artifacts(
                    run_id=run.id,
                    task_id=task_id,
                )
                if consumed_artifact_ids is None:
                    artifact_blocked = True
                    if blocked_task_id is None:
                        blocked_task_id = task_id
                        blocked_requirements = missing_requirements
                    continue
                return task_id, None, consumed_artifact_ids
            dependency_blocked = True

        if dependency_blocked:
            return None, "dependencies not satisfied", []
        if artifact_blocked:
            if blocked_task_id is not None:
                self._append_event(
                    event_type="task.dispatch_blocked_missing_handoff_artifacts",
                    run_id=run_id,
                    task_id=blocked_task_id,
                    payload={"missing_requirements": blocked_requirements},
                )
            return None, "required handoff artifacts missing", []
        return None, "no ready tasks", []

    def plan_workflow_run_dispatch(self, run_id: int, *, max_tasks: int = 100) -> WorkflowRunDispatchPlan:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")

        if max_tasks <= 0:
            return WorkflowRunDispatchPlan()

        plan = WorkflowRunDispatchPlan()
        if run.status == WorkflowRunStatus.ABORTED.value:
            plan.blocked.append(
                WorkflowRunDispatchBlockedItem(
                    task_id=None,
                    reason="run-aborted",
                    details={"run_id": run_id},
                )
            )
            return plan
        if run.status == WorkflowRunStatus.PAUSED.value:
            plan.blocked.append(
                WorkflowRunDispatchBlockedItem(
                    task_id=None,
                    reason="run-paused",
                    details={"run_id": run_id},
                )
            )
            return plan

        for task_id in run.task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status not in (TaskStatus.CREATED.value, TaskStatus.SUBMIT_FAILED.value):
                continue

            dependencies = run.step_dependencies.get(task_id, [])
            unresolved_dependencies: list[dict[str, Any]] = []
            for dependency_task_id in dependencies:
                dependency_task = self._tasks.get(dependency_task_id)
                dependency_status = (
                    dependency_task.status
                    if dependency_task is not None
                    else "missing"
                )
                if dependency_status != TaskStatus.SUCCESS.value:
                    unresolved_dependencies.append(
                        {"task_id": dependency_task_id, "status": dependency_status}
                    )
            if unresolved_dependencies:
                plan.blocked.append(
                    WorkflowRunDispatchBlockedItem(
                        task_id=task_id,
                        reason="dependencies-not-satisfied",
                        details={"dependencies": unresolved_dependencies},
                    )
                )
                continue

            consumed_artifact_ids, missing_requirements = self._resolve_handoff_artifacts(
                run_id=run_id,
                task_id=task_id,
            )
            if consumed_artifact_ids is None:
                plan.blocked.append(
                    WorkflowRunDispatchBlockedItem(
                        task_id=task_id,
                        reason="required-handoff-artifacts-missing",
                        details={"missing_requirements": missing_requirements},
                    )
                )
                continue

            approval_status = self._approval_status_for_task(task_id)
            if task.requires_approval and approval_status != ApprovalStatus.APPROVED:
                approval_id = self._task_approval.get(task_id)
                plan.blocked.append(
                    WorkflowRunDispatchBlockedItem(
                        task_id=task_id,
                        reason="approval-required",
                        details={
                            "approval_id": approval_id,
                            "approval_status": approval_status.value if approval_status is not None else "missing",
                        },
                    )
                )
                continue

            if len(plan.ready) >= max_tasks:
                plan.blocked.append(
                    WorkflowRunDispatchBlockedItem(
                        task_id=task_id,
                        reason="dispatch-limit-reached",
                        details={"max_tasks": max_tasks},
                    )
                )
                continue

            plan.ready.append(
                WorkflowRunDispatchPlanItem(
                    task_id=task_id,
                    consumed_artifact_ids=consumed_artifact_ids,
                )
            )
        return plan

    def get_workflow_run_execution_summary(self, run_id: int) -> WorkflowRunExecutionSummary:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")

        status_counts: dict[str, int] = {}
        successful_task_ids: list[int] = []
        failed_task_ids: list[int] = []
        active_task_ids: list[int] = []
        pending_task_ids: list[int] = []
        task_summaries: list[WorkflowRunExecutionTaskSummary] = []

        for task_id in run.task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue

            status_counts[task.status] = status_counts.get(task.status, 0) + 1
            if task.status == TaskStatus.SUCCESS.value:
                successful_task_ids.append(task_id)
            elif task.status in (
                TaskStatus.FAILED.value,
                TaskStatus.CANCELED.value,
                TaskStatus.SUBMIT_FAILED.value,
            ):
                failed_task_ids.append(task_id)
            elif task.status in (
                TaskStatus.DISPATCHED.value,
                TaskStatus.QUEUED.value,
                TaskStatus.RUNNING.value,
                TaskStatus.CANCEL_REQUESTED.value,
            ):
                active_task_ids.append(task_id)
            else:
                pending_task_ids.append(task_id)

            approval_status = self._approval_status_for_task(task_id)
            audit = self._audits.get(task_id)
            handoff = self._handoffs.get(task_id)
            task_summaries.append(
                WorkflowRunExecutionTaskSummary(
                    task_id=task.id,
                    title=task.title,
                    role_id=task.role_id,
                    status=task.status,
                    runner_message=task.runner_message,
                    started_at=task.started_at,
                    finished_at=task.finished_at,
                    exit_code=task.exit_code,
                    requires_approval=task.requires_approval,
                    approval_status=approval_status,
                    consumed_artifact_ids=(list(audit.consumed_artifact_ids) if audit is not None else []),
                    produced_artifact_ids=(list(audit.produced_artifact_ids) if audit is not None else []),
                    handoff_summary=handoff.summary if handoff is not None else None,
                    quality_gate_summary=self._evaluate_task_quality_gates(
                        task,
                        policy=self._task_quality_gate_policy(task),
                    ),
                )
            )

        total_tasks = len(task_summaries)
        done_count = len(successful_task_ids)
        blocked_count = len(failed_task_ids) + len(pending_task_ids)
        active_count = len(active_task_ids)
        progress_percent = round(((done_count + len(failed_task_ids)) / total_tasks) * 100, 2) if total_tasks else 0.0

        return WorkflowRunExecutionSummary(
            run=self._to_workflow_run_read(run),
            task_status_counts=status_counts,
            terminal=run.status in (
                WorkflowRunStatus.SUCCESS.value,
                WorkflowRunStatus.FAILED.value,
                WorkflowRunStatus.ABORTED.value,
            ),
            partial_completion=bool(successful_task_ids) and len(successful_task_ids) < len(task_summaries),
            progress_percent=progress_percent,
            branch_status_cards={"active": active_count, "blocked": blocked_count, "done": done_count},
            next_dispatch=self.plan_workflow_run_dispatch(run_id, max_tasks=max(len(run.task_ids), 1)),
            successful_task_ids=successful_task_ids,
            failed_task_ids=failed_task_ids,
            active_task_ids=active_task_ids,
            pending_task_ids=pending_task_ids,
            tasks=task_summaries,
        )

    def create_event(self, event: EventCreate) -> EventRead:
        if event.run_id is not None and event.run_id not in self._workflow_runs:
            raise NotFoundError(f"workflow run {event.run_id} not found")
        if event.task_id is not None and event.task_id not in self._tasks:
            raise NotFoundError(f"task {event.task_id} not found")
        created = self._append_event(
            event_type=event.event_type,
            run_id=event.run_id,
            task_id=event.task_id,
            producer_role=event.producer_role,
            payload=event.payload,
        )
        self._persist_state()
        return created

    def list_events(
        self,
        *,
        run_id: int | None = None,
        task_id: int | None = None,
        event_type: str | None = None,
        limit: int = 200,
    ) -> list[EventRead]:
        if limit <= 0:
            return []

        filtered = [
            event
            for event in self._events
            if (run_id is None or event.run_id == run_id)
            and (task_id is None or event.task_id == task_id)
            and (event_type is None or event.event_type == event_type)
        ]
        return filtered[-limit:]

    def create_artifact(self, artifact: ArtifactCreate) -> ArtifactRead:
        if artifact.producer_task_id not in self._tasks:
            raise NotFoundError(f"task {artifact.producer_task_id} not found")
        if artifact.task_id is not None and artifact.task_id not in self._tasks:
            raise NotFoundError(f"task {artifact.task_id} not found")
        if artifact.run_id is not None and artifact.run_id not in self._workflow_runs:
            raise NotFoundError(f"workflow run {artifact.run_id} not found")

        created = ArtifactRead(
            id=self._artifact_seq,
            artifact_type=artifact.artifact_type,
            location=artifact.location,
            summary=artifact.summary,
            producer_task_id=artifact.producer_task_id,
            run_id=artifact.run_id,
            task_id=artifact.task_id,
            metadata=artifact.metadata,
            created_at=self._utc_now(),
        )
        self._artifact_seq += 1
        self._artifacts.append(created)
        if created.task_id is not None:
            audit = self._audits.get(created.task_id)
            if audit is not None:
                audit.produced_artifact_ids.append(created.id)
                self._audits[created.task_id] = audit
        self._append_event(
            event_type="artifact.created",
            run_id=created.run_id,
            task_id=created.task_id,
            producer_role="system",
            payload={
                "artifact_id": created.id,
                "artifact_type": created.artifact_type.value,
                "location": created.location,
                "producer_task_id": created.producer_task_id,
            },
        )
        self._persist_state()
        return created

    def list_artifacts(
        self,
        *,
        run_id: int | None = None,
        task_id: int | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int = 200,
    ) -> list[ArtifactRead]:
        if limit <= 0:
            return []

        filtered = [
            artifact
            for artifact in self._artifacts
            if (run_id is None or artifact.run_id == run_id)
            and (task_id is None or artifact.task_id == task_id)
            and (artifact_type is None or artifact.artifact_type == artifact_type)
        ]
        return filtered[-limit:]

    def list_handoffs(
        self,
        *,
        run_id: int | None = None,
        task_id: int | None = None,
        limit: int = 200,
    ) -> list[TaskHandoffRead]:
        if limit <= 0:
            return []
        filtered = [
            handoff
            for handoff in self._handoffs.values()
            if (run_id is None or handoff.run_id == run_id)
            and (task_id is None or handoff.task_id == task_id)
        ]
        filtered.sort(key=lambda item: item.updated_at)
        return filtered[-limit:]

    def get_task_handoff(self, task_id: int) -> TaskHandoffRead:
        if task_id not in self._tasks:
            raise NotFoundError(f"task {task_id} not found")
        handoff = self._handoffs.get(task_id)
        if handoff is None:
            raise NotFoundError(f"handoff for task {task_id} not found")
        return handoff

    def create_role(self, role: RoleCreate) -> RoleRead:
        self._validate_role_skill_packs(role.skill_packs)
        role_id = self._role_seq
        self._role_seq += 1
        record = _RoleRecord(
            id=role_id,
            name=role.name,
            context7_enabled=role.context7_enabled,
            system_prompt=role.system_prompt,
            allowed_tools=role.allowed_tools,
            skill_packs=role.skill_packs,
            execution_constraints=role.execution_constraints,
        )
        self._roles[role_id] = record
        self._persist_state()
        return RoleRead(
            id=record.id,
            name=record.name,
            context7_enabled=record.context7_enabled,
            system_prompt=record.system_prompt,
            allowed_tools=record.allowed_tools,
            skill_packs=record.skill_packs,
            execution_constraints=record.execution_constraints,
        )

    def list_roles(self) -> list[RoleRead]:
        return [
            RoleRead(
                id=record.id,
                name=record.name,
                context7_enabled=record.context7_enabled,
                system_prompt=record.system_prompt,
                allowed_tools=record.allowed_tools,
                skill_packs=record.skill_packs,
                execution_constraints=record.execution_constraints,
            )
            for record in self._roles.values()
        ]

    def get_role(self, role_id: int) -> RoleRead:
        record = self._roles.get(role_id)
        if record is None:
            raise NotFoundError(f"role {role_id} not found")
        return RoleRead(
            id=record.id,
            name=record.name,
            context7_enabled=record.context7_enabled,
            system_prompt=record.system_prompt,
            allowed_tools=record.allowed_tools,
            skill_packs=record.skill_packs,
            execution_constraints=record.execution_constraints,
        )

    def update_role(
        self,
        role_id: int,
        *,
        name: str,
        context7_enabled: bool,
        system_prompt: str,
        allowed_tools: list[str],
        skill_packs: list[str],
        execution_constraints: dict[str, Any],
    ) -> RoleRead:
        record = self._roles.get(role_id)
        if record is None:
            raise NotFoundError(f"role {role_id} not found")
        self._validate_role_skill_packs(skill_packs)
        updated = _RoleRecord(
            id=record.id,
            name=name,
            context7_enabled=context7_enabled,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            skill_packs=skill_packs,
            execution_constraints=execution_constraints,
        )
        self._roles[role_id] = updated
        self._persist_state()
        return RoleRead(
            id=updated.id,
            name=updated.name,
            context7_enabled=updated.context7_enabled,
            system_prompt=updated.system_prompt,
            allowed_tools=updated.allowed_tools,
            skill_packs=updated.skill_packs,
            execution_constraints=updated.execution_constraints,
        )

    def delete_role(self, role_id: int) -> None:
        if role_id not in self._roles:
            raise NotFoundError(f"role {role_id} not found")
        for task in self._tasks.values():
            if task.role_id == role_id:
                raise ConflictError(f"role {role_id} has linked tasks")
        del self._roles[role_id]
        self._persist_state()

    def create_task(self, task: TaskCreate) -> TaskRead:
        if task.role_id not in self._roles:
            raise NotFoundError(f"role {task.role_id} not found")
        if task.project_id is not None and task.project_id not in self._projects:
            raise NotFoundError(f"project {task.project_id} not found")

        normalized_lock_paths = task.lock_paths
        if task.execution_mode == ExecutionMode.SHARED_WORKSPACE:
            if task.project_id is None:
                raise ValidationError("project_id is required for shared-workspace mode")
            normalized_lock_paths = self._normalize_shared_lock_paths(task.project_id, task.lock_paths)

        task_id = self._task_seq
        self._task_seq += 1
        record = _TaskRecord(
            id=task_id,
            role_id=task.role_id,
            title=task.title,
            context7_mode=task.context7_mode.value,
            execution_mode=task.execution_mode.value,
            requires_approval=task.requires_approval,
            project_id=task.project_id,
            lock_paths=normalized_lock_paths,
            sandbox=task.sandbox.model_dump() if task.sandbox is not None else None,
            quality_gate_policy=task.quality_gate_policy.model_dump(),
            status=TaskStatus.CREATED.value,
        )
        self._tasks[task_id] = record
        if record.requires_approval:
            approval = self._create_pending_approval(task_id)
            self._task_approval[task_id] = approval.id

        self._append_event(
            event_type="task.created",
            task_id=task_id,
            payload={
                "role_id": task.role_id,
                "execution_mode": task.execution_mode.value,
                "requires_approval": task.requires_approval,
            },
        )
        self._persist_state()

        return self._to_task_read(record)

    def get_task(self, task_id: int) -> TaskRead:
        record = self._tasks.get(task_id)
        if record is None:
            raise NotFoundError(f"task {task_id} not found")
        return self._to_task_read(record)

    def list_tasks(self, *, run_id: int | None = None) -> list[TaskRead]:
        if run_id is not None:
            run = self._workflow_runs.get(run_id)
            if run is None:
                raise NotFoundError(f"workflow run {run_id} not found")
            run_task_ids = set(run.task_ids)
            records = [record for record in self._tasks.values() if record.id in run_task_ids]
        else:
            records = list(self._tasks.values())
        return [self._to_task_read(record) for record in records]

    def dispatch_task(self, task_id: int, *, consumed_artifact_ids: list[int] | None = None) -> DispatchResponse:
        task = self.get_task(task_id)
        if task.status not in (TaskStatus.CREATED, TaskStatus.SUBMIT_FAILED):
            raise ConflictError(f"task {task_id} is not dispatchable from status '{task.status.value}'")
        role = self.get_role(task.role_id)
        run_id = self._task_latest_run.get(task.id)
        task_run_id = self._task_run_id(task.id, run_id)
        resolved = resolve_context7_enabled(
            role_context7_enabled=role.context7_enabled,
            task_mode=task.context7_mode,
        )
        approval_status = self._require_approval_ready(
            task_id=task.id,
            requires_approval=task.requires_approval,
            run_id=run_id,
        )

        workspace = (
            self._acquire_shared_workspace(task_id=task.id, project_id=task.project_id, lock_paths=task.lock_paths)
            if task.execution_mode == ExecutionMode.SHARED_WORKSPACE
            else (
                self._acquire_isolated_workspace(task_id=task.id, run_id=run_id, project_id=task.project_id)
                if task.execution_mode == ExecutionMode.ISOLATED_WORKTREE
                else (
                    self._build_docker_workspace(project_id=task.project_id)
                    if task.execution_mode == ExecutionMode.DOCKER_SANDBOX
                    else None
                )
            )
        )
        sandbox = (
            self._build_docker_sandbox(project_id=task.project_id, sandbox=task.sandbox)
            if task.execution_mode == ExecutionMode.DOCKER_SANDBOX
            else None
        )
        handoff_context = self._build_handoff_context(run_id=run_id, task_id=task.id)

        payload = RunnerSubmitPayload(
            task_id=task.id,
            run_id=run_id,
            role_id=task.role_id,
            title=task.title,
            execution_mode=task.execution_mode,
            role_skill_packs=role.skill_packs,
            context=RunnerContext(enabled=resolved),
            workspace=workspace,
            sandbox=sandbox,
            handoff_context=handoff_context,
        )

        if consumed_artifact_ids is None:
            consumed_artifact_ids = []

        previous_audit = self._audits.get(task.id)
        self._audits[task.id] = TaskAudit(
            task_id=task.id,
            role_id=task.role_id,
            context7_mode=task.context7_mode,
            role_context7_enabled=role.context7_enabled,
            resolved_context7_enabled=resolved,
            execution_mode=task.execution_mode,
            requires_approval=task.requires_approval,
            approval_status=approval_status,
            workflow_run_id=run_id,
            task_run_id=task_run_id,
            project_id=task.project_id,
            lock_paths=task.lock_paths,
            worktree_path=workspace.worktree_path if workspace is not None else None,
            git_branch=workspace.git_branch if workspace is not None else None,
            worktree_cleanup_attempted=False,
            worktree_cleanup_succeeded=None,
            worktree_cleanup_message=None,
            worktree_cleanup_at=None,
            sandbox_image=sandbox.image if sandbox is not None else None,
            sandbox_workdir=sandbox.workdir if sandbox is not None else None,
            sandbox_container_id=None,
            sandbox_exit_code=None,
            sandbox_error=None,
            handoff=self._handoffs.get(task.id),
            consumed_artifact_ids=consumed_artifact_ids,
            produced_artifact_ids=list(previous_audit.produced_artifact_ids) if previous_audit is not None else [],
            retry_attempts=previous_audit.retry_attempts if previous_audit is not None else 0,
            last_retry_reason=previous_audit.last_retry_reason if previous_audit is not None else None,
            failure_categories=list(previous_audit.failure_categories) if previous_audit is not None else [],
            failure_triage_hints=list(previous_audit.failure_triage_hints) if previous_audit is not None else [],
            recent_event_ids=list(previous_audit.recent_event_ids) if previous_audit is not None else [],
        )
        record = self._tasks.get(task.id)
        if record is None:
            raise NotFoundError(f"task {task.id} not found")
        record.status = TaskStatus.DISPATCHED.value
        record.runner_message = "dispatch accepted"
        self._tasks[task.id] = record

        self._append_event(
            event_type="task.dispatched",
            run_id=run_id,
            task_id=task.id,
            payload={
                "execution_mode": task.execution_mode.value,
                "context7_enabled": resolved,
                "requires_approval": task.requires_approval,
                "consumed_artifact_ids": consumed_artifact_ids,
                "handoff_context_task_ids": [item.task_id for item in handoff_context],
                "task_run_id": task_run_id,
                "worktree_path": workspace.worktree_path if workspace is not None else None,
                "git_branch": workspace.git_branch if workspace is not None else None,
            },
        )
        if run_id is not None:
            self._recompute_workflow_run_status(run_id)
        self._persist_state()

        return DispatchResponse(
            task_id=task.id,
            resolved_context7_enabled=resolved,
            runner_payload=payload,
        )

    def apply_runner_submission(self, task_id: int, submission: RunnerSubmission) -> TaskRead:
        record = self._tasks.get(task_id)
        if record is None:
            raise NotFoundError(f"task {task_id} not found")

        run_id = self._task_latest_run.get(task_id)
        event_payload: dict[str, Any] = {
            "submitted": submission.submitted,
            "runner_url": submission.runner_url,
            "message": submission.message,
            "runner_task_status": submission.runner_task_status,
        }
        if submission.submitted:
            record.status = TaskStatus.QUEUED.value
            record.runner_message = submission.message or "submitted"
            event_type = "task.runner_queued"
        else:
            record.status = TaskStatus.SUBMIT_FAILED.value
            record.runner_message = submission.message or "runner submit failed"
            audit = self._audits.get(task_id)
            if audit is not None and audit.execution_mode == ExecutionMode.DOCKER_SANDBOX:
                audit.sandbox_error = record.runner_message
                self._audits[task_id] = audit
            retry_decision = self._evaluate_retry_for_failure(
                task_id=task_id,
                failure_status=TaskStatus.SUBMIT_FAILED.value,
                message=record.runner_message,
                exit_code=record.exit_code,
                stdout=record.stdout,
                stderr=record.stderr,
            )
            event_payload["failure_category"] = retry_decision["failure_category"]
            event_payload["recovery_hint"] = retry_decision["recovery_hint"]
            event_payload["retry_scheduled"] = retry_decision["retry_scheduled"]
            event_payload["retry_attempt"] = retry_decision["retry_attempt"]
            event_payload["max_retries"] = retry_decision["max_retries"]
            event_payload["retries_remaining"] = retry_decision["retries_remaining"]
            event_payload["retry_reason"] = retry_decision["retry_reason"]
            if retry_decision["retry_scheduled"]:
                record.status = TaskStatus.CREATED.value
                record.runner_message = retry_decision["retry_reason"]
                record.started_at = None
                record.finished_at = None
                record.exit_code = None
                record.stdout = None
                record.stderr = None
                self._append_event(
                    event_type="task.retry_scheduled",
                    run_id=run_id,
                    task_id=task_id,
                    payload={
                        "trigger_status": TaskStatus.SUBMIT_FAILED.value,
                        "failure_category": retry_decision["failure_category"],
                        "retry_attempt": retry_decision["retry_attempt"],
                        "max_retries": retry_decision["max_retries"],
                        "retries_remaining": retry_decision["retries_remaining"],
                        "retry_reason": retry_decision["retry_reason"],
                        "recovery_hint": retry_decision["recovery_hint"],
                    },
                )
            else:
                released_paths = self._release_task_locks_internal(task_id=task_id, run_id=run_id, emit_event=True)
                event_payload["released_paths"] = released_paths
                released_session = self._release_isolated_session_internal(
                    task_id=task_id,
                    run_id=run_id,
                    reason="runner-submit-failed",
                    cleanup_attempted=False,
                    cleanup_succeeded=None,
                    cleanup_message="runner submission failed before execution",
                )
                if released_session is not None:
                    event_payload["released_worktree_path"] = released_session.worktree_path
                    event_payload["released_git_branch"] = released_session.git_branch
            event_type = "task.runner_submit_failed"

        self._tasks[task_id] = record
        self._append_event(
            event_type=event_type,
            run_id=run_id,
            task_id=task_id,
            payload=event_payload,
        )
        if run_id is not None:
            self._recompute_workflow_run_status(run_id)
        self._persist_state()
        return self.get_task(task_id)

    def apply_runner_cancel_request(self, task_id: int, submission: RunnerSubmission) -> TaskRead:
        record = self._tasks.get(task_id)
        if record is None:
            raise NotFoundError(f"task {task_id} not found")

        if self._is_terminal_task_status(record.status):
            return self.get_task(task_id)

        run_id = self._task_latest_run.get(task_id)
        event_payload: dict[str, Any] = {
            "submitted": submission.submitted,
            "runner_url": submission.runner_url,
            "message": submission.message,
            "runner_task_status": submission.runner_task_status,
        }

        if submission.submitted:
            if submission.runner_task_status == TaskStatus.CANCELED.value:
                record.status = TaskStatus.CANCELED.value
                released_paths = self._release_task_locks_internal(task_id=task_id, run_id=run_id, emit_event=True)
                event_payload["released_paths"] = released_paths
                released_session = self._release_isolated_session_internal(
                    task_id=task_id,
                    run_id=run_id,
                    reason="cancel-requested",
                    cleanup_attempted=False,
                    cleanup_succeeded=None,
                    cleanup_message="cancel accepted by runner",
                )
                if released_session is not None:
                    event_payload["released_worktree_path"] = released_session.worktree_path
                    event_payload["released_git_branch"] = released_session.git_branch
            else:
                record.status = TaskStatus.CANCEL_REQUESTED.value
            record.runner_message = submission.message or "cancel requested"
            event_type = "task.runner_cancel_requested"
        else:
            record.runner_message = submission.message or "runner cancel failed"
            event_type = "task.runner_cancel_failed"

        self._tasks[task_id] = record
        self._append_event(
            event_type=event_type,
            run_id=run_id,
            task_id=task_id,
            payload=event_payload,
        )
        if run_id is not None:
            self._recompute_workflow_run_status(run_id)
        self._persist_state()
        return self.get_task(task_id)

    def update_task_runner_status(
        self,
        task_id: int,
        *,
        status: RunnerLifecycleStatus,
        message: str | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        exit_code: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        container_id: str | None = None,
        worktree_cleanup_attempted: bool | None = None,
        worktree_cleanup_succeeded: bool | None = None,
        worktree_cleanup_message: str | None = None,
        handoff: TaskHandoffPayload | None = None,
    ) -> TaskRead:
        record = self._tasks.get(task_id)
        if record is None:
            raise NotFoundError(f"task {task_id} not found")

        run_id = self._task_latest_run.get(task_id)
        is_terminal = status in (
            RunnerLifecycleStatus.SUCCESS,
            RunnerLifecycleStatus.FAILED,
            RunnerLifecycleStatus.CANCELED,
        )
        record.status = status.value
        if message is not None:
            record.runner_message = message
        if started_at is not None:
            record.started_at = started_at
        if status == RunnerLifecycleStatus.RUNNING and record.started_at is None:
            record.started_at = self._utc_now()
        if exit_code is not None:
            record.exit_code = exit_code
        if stdout is not None:
            record.stdout = stdout
        if stderr is not None:
            record.stderr = stderr
        if finished_at is not None:
            record.finished_at = finished_at
        if is_terminal and record.finished_at is None:
            record.finished_at = self._utc_now()

        self._tasks[task_id] = record
        audit = self._audits.get(task_id)
        if audit is not None and audit.execution_mode == ExecutionMode.DOCKER_SANDBOX:
            if container_id is not None:
                audit.sandbox_container_id = container_id
            if exit_code is not None:
                audit.sandbox_exit_code = exit_code
            if status in (RunnerLifecycleStatus.FAILED, RunnerLifecycleStatus.CANCELED) and message is not None:
                audit.sandbox_error = message
            self._audits[task_id] = audit
        elif audit is not None and audit.execution_mode == ExecutionMode.ISOLATED_WORKTREE:
            has_cleanup_update = (
                worktree_cleanup_attempted is not None
                or worktree_cleanup_succeeded is not None
                or worktree_cleanup_message is not None
            )
            if worktree_cleanup_attempted is not None:
                audit.worktree_cleanup_attempted = worktree_cleanup_attempted
            if worktree_cleanup_succeeded is not None:
                audit.worktree_cleanup_succeeded = worktree_cleanup_succeeded
            if worktree_cleanup_message is not None:
                audit.worktree_cleanup_message = worktree_cleanup_message
            if has_cleanup_update:
                audit.worktree_cleanup_at = self._utc_now()
            self._audits[task_id] = audit

        event_payload: dict[str, Any] = {
            "status": status.value,
            "message": message,
            "exit_code": exit_code,
            "container_id": container_id,
            "worktree_cleanup_attempted": worktree_cleanup_attempted,
            "worktree_cleanup_succeeded": worktree_cleanup_succeeded,
            "worktree_cleanup_message": worktree_cleanup_message,
        }
        retry_decision: dict[str, Any] | None = None
        if status == RunnerLifecycleStatus.FAILED:
            retry_decision = self._evaluate_retry_for_failure(
                task_id=task_id,
                failure_status=TaskStatus.FAILED.value,
                message=message,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
            )
            event_payload["failure_category"] = retry_decision["failure_category"]
            event_payload["recovery_hint"] = retry_decision["recovery_hint"]
            event_payload["retry_scheduled"] = retry_decision["retry_scheduled"]
            event_payload["retry_attempt"] = retry_decision["retry_attempt"]
            event_payload["max_retries"] = retry_decision["max_retries"]
            event_payload["retries_remaining"] = retry_decision["retries_remaining"]
            event_payload["retry_reason"] = retry_decision["retry_reason"]
            if retry_decision["retry_scheduled"]:
                record.status = TaskStatus.CREATED.value
                record.runner_message = retry_decision["retry_reason"]
                record.started_at = None
                record.finished_at = None
                record.exit_code = None
                record.stdout = None
                record.stderr = None
                self._tasks[task_id] = record

        if handoff is not None and not is_terminal:
            raise ValidationError("handoff payload is accepted only for terminal task status updates")
        if handoff is not None:
            saved_handoff = self._upsert_task_handoff(
                task_id=task_id,
                run_id=run_id,
                handoff=handoff,
            )
            event_payload["handoff_updated_at"] = saved_handoff.updated_at
            event_payload["handoff_required_artifact_ids"] = [
                item.artifact_id for item in saved_handoff.artifacts if item.is_required
            ]
            audit = self._audits.get(task_id)
            if audit is not None:
                audit.handoff = saved_handoff
                self._audits[task_id] = audit

        if is_terminal and not (retry_decision is not None and retry_decision["retry_scheduled"]):
            released_paths = self._release_task_locks_internal(task_id=task_id, run_id=run_id, emit_event=True)
            event_payload["released_paths"] = released_paths
            released_session = self._release_isolated_session_internal(
                task_id=task_id,
                run_id=run_id,
                reason=f"runner-status-{status.value}",
                cleanup_attempted=worktree_cleanup_attempted,
                cleanup_succeeded=worktree_cleanup_succeeded,
                cleanup_message=worktree_cleanup_message,
            )
            if released_session is not None:
                event_payload["released_worktree_path"] = released_session.worktree_path
                event_payload["released_git_branch"] = released_session.git_branch
        if retry_decision is not None and retry_decision["retry_scheduled"]:
            self._append_event(
                event_type="task.retry_scheduled",
                run_id=run_id,
                task_id=task_id,
                payload={
                    "trigger_status": status.value,
                    "failure_category": retry_decision["failure_category"],
                    "retry_attempt": retry_decision["retry_attempt"],
                    "max_retries": retry_decision["max_retries"],
                    "retries_remaining": retry_decision["retries_remaining"],
                    "retry_reason": retry_decision["retry_reason"],
                    "recovery_hint": retry_decision["recovery_hint"],
                },
            )
        self._append_event(
            event_type="task.runner_status_updated",
            run_id=run_id,
            task_id=task_id,
            payload=event_payload,
        )
        if audit is not None and audit.execution_mode == ExecutionMode.DOCKER_SANDBOX:
            sandbox_event_type = (
                "sandbox.started"
                if status == RunnerLifecycleStatus.RUNNING
                else (
                    "sandbox.failed"
                    if status == RunnerLifecycleStatus.FAILED
                    else (
                        "sandbox.stopped"
                        if status in (RunnerLifecycleStatus.SUCCESS, RunnerLifecycleStatus.CANCELED)
                        else None
                    )
                )
            )
            if sandbox_event_type is not None:
                self._append_event(
                    event_type=sandbox_event_type,
                    run_id=run_id,
                    task_id=task_id,
                    payload={
                        "container_id": container_id,
                        "status": status.value,
                        "message": message,
                        "exit_code": exit_code,
                    },
                )
        if run_id is not None:
            self._recompute_workflow_run_status(run_id)
        self._persist_state()
        return self.get_task(task_id)

    def get_task_audit(self, task_id: int) -> TaskAudit:
        audit = self._audits.get(task_id)
        if audit is None:
            raise NotFoundError(f"audit for task {task_id} not found")
        return audit

    def get_task_approval(self, task_id: int) -> ApprovalRead:
        if task_id not in self._tasks:
            raise NotFoundError(f"task {task_id} not found")
        approval_id = self._task_approval.get(task_id)
        if approval_id is None:
            raise NotFoundError(f"task {task_id} has no approval gate")
        return self.get_approval(approval_id)

    def get_approval(self, approval_id: int) -> ApprovalRead:
        record = self._approvals.get(approval_id)
        if record is None:
            raise NotFoundError(f"approval {approval_id} not found")
        return self._to_approval_read(record)

    def approve_approval(self, approval_id: int, *, actor: str | None, comment: str | None) -> ApprovalRead:
        return self._set_approval_status(
            approval_id,
            status=ApprovalStatus.APPROVED.value,
            actor=actor,
            comment=comment,
        )

    def reject_approval(self, approval_id: int, *, actor: str | None, comment: str | None) -> ApprovalRead:
        return self._set_approval_status(
            approval_id,
            status=ApprovalStatus.REJECTED.value,
            actor=actor,
            comment=comment,
        )

    def release_task_locks(self, task_id: int) -> list[str]:
        if task_id not in self._tasks:
            raise NotFoundError(f"task {task_id} not found")

        run_id = self._task_latest_run.get(task_id)
        released_paths = self._release_task_locks_internal(task_id=task_id, run_id=run_id, emit_event=True)
        self._persist_state()
        return released_paths

    def _assistant_plan_steps(
        self,
        template: _WorkflowTemplateRecord,
        step_task_overrides: dict[str, WorkflowRunStepTaskOverride],
    ) -> list[AssistantPlanStepRead]:
        known_step_ids = {step.step_id for step in template.steps}
        unknown_step_ids = sorted(set(step_task_overrides) - known_step_ids)
        if unknown_step_ids:
            unknown_joined = ", ".join(unknown_step_ids)
            raise ValidationError(f"unknown workflow step overrides: {unknown_joined}")

        steps: list[AssistantPlanStepRead] = []
        for step in template.steps:
            resolved_config = self._resolve_step_task_override(
                template_project_id=template.project_id,
                override=step_task_overrides.get(step.step_id),
            )
            if resolved_config.project_id is not None and resolved_config.project_id not in self._projects:
                raise NotFoundError(f"project {resolved_config.project_id} not found")
            steps.append(
                AssistantPlanStepRead(
                    step_id=step.step_id,
                    role_id=step.role_id,
                    title=step.title,
                    depends_on=step.depends_on,
                    required_artifacts=step.required_artifacts,
                    quality_gate_policy=step.quality_gate_policy,
                    task_config=resolved_config,
                )
            )
        return steps

    @staticmethod
    def _resolve_step_task_override(
        *,
        template_project_id: int | None,
        override: WorkflowRunStepTaskOverride | None,
    ) -> WorkflowRunStepTaskOverride:
        effective = override or WorkflowRunStepTaskOverride()
        project_id = effective.project_id
        if project_id is None and effective.execution_mode != ExecutionMode.NO_WORKSPACE:
            project_id = template_project_id
        try:
            return WorkflowRunStepTaskOverride(
                context7_mode=effective.context7_mode,
                execution_mode=effective.execution_mode,
                requires_approval=effective.requires_approval,
                project_id=project_id,
                lock_paths=effective.lock_paths,
                sandbox=effective.sandbox,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def _assistant_dispatch_candidates(self, run_id: int) -> tuple[list[tuple[int, list[int]]], list[int]]:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")

        ready: list[tuple[int, list[int]]] = []
        blocked_by_approval: list[int] = []
        for task_id in run.task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            if task.status not in (TaskStatus.CREATED.value, TaskStatus.SUBMIT_FAILED.value):
                continue

            dependencies = run.step_dependencies.get(task_id, [])
            dependencies_ready = all(
                self._tasks.get(dep_task_id) is not None
                and self._tasks[dep_task_id].status == TaskStatus.SUCCESS.value
                for dep_task_id in dependencies
            )
            if not dependencies_ready:
                continue

            consumed_artifact_ids, _missing_requirements = self._resolve_handoff_artifacts(
                run_id=run_id,
                task_id=task_id,
            )
            if consumed_artifact_ids is None:
                continue

            approval_status = self._approval_status_for_task(task_id)
            if task.requires_approval and approval_status != ApprovalStatus.APPROVED:
                blocked_by_approval.append(task_id)
                continue

            ready.append((task_id, consumed_artifact_ids))
        return ready, blocked_by_approval

    def _approval_status_for_task(self, task_id: int) -> ApprovalStatus | None:
        task = self._tasks.get(task_id)
        if task is None or not task.requires_approval:
            return None
        approval_id = self._task_approval.get(task_id)
        if approval_id is None:
            return None
        approval = self._approvals.get(approval_id)
        if approval is None:
            return None
        return ApprovalStatus(approval.status)

    def _build_assistant_machine_summary(
        self,
        *,
        run_id: int,
        phase: str,
        preloaded_events: list[EventRead] | None = None,
        preloaded_artifacts: list[ArtifactRead] | None = None,
        preloaded_handoffs: list[TaskHandoffRead] | None = None,
    ) -> AssistantMachineSummary:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")

        task_records = [self._tasks[task_id] for task_id in run.task_ids if task_id in self._tasks]
        status_counts: dict[str, int] = {}
        for task in task_records:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        ready_candidates, blocked_by_approval_task_ids = self._assistant_dispatch_candidates(run_id)
        terminal_task_ids = [task.id for task in task_records if self._is_terminal_task_status(task.status)]
        failed_task_ids = [
            task.id
            for task in task_records
            if task.status in (TaskStatus.FAILED.value, TaskStatus.CANCELED.value, TaskStatus.SUBMIT_FAILED.value)
        ]

        artifacts = preloaded_artifacts if preloaded_artifacts is not None else self.list_artifacts(run_id=run_id, limit=200)
        handoffs = preloaded_handoffs if preloaded_handoffs is not None else self.list_handoffs(run_id=run_id, limit=200)
        events = preloaded_events if preloaded_events is not None else self.list_events(run_id=run_id, limit=50)

        produced_artifact_ids: list[int] = []
        for artifact in artifacts:
            if artifact.id in produced_artifact_ids:
                continue
            produced_artifact_ids.append(artifact.id)

        handoff_task_ids: list[int] = []
        for handoff in handoffs:
            if handoff.task_id in handoff_task_ids:
                continue
            handoff_task_ids.append(handoff.task_id)

        recent_event_types: list[str] = []
        for event in events[-20:]:
            if event.event_type in recent_event_types:
                continue
            recent_event_types.append(event.event_type)

        return AssistantMachineSummary(
            phase=phase,
            run_id=run_id,
            workflow_template_id=run.workflow_template_id,
            workflow_status=run.status,
            total_tasks=len(run.task_ids),
            task_status_counts=status_counts,
            ready_task_ids=[task_id for task_id, _ in ready_candidates],
            blocked_by_approval_task_ids=blocked_by_approval_task_ids,
            terminal_task_ids=terminal_task_ids,
            failed_task_ids=failed_task_ids,
            produced_artifact_ids=produced_artifact_ids,
            handoff_task_ids=handoff_task_ids,
            recent_event_types=recent_event_types,
        )

    def _resolve_handoff_artifacts(self, *, run_id: int, task_id: int) -> tuple[list[int] | None, list[dict[str, Any]]]:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")
        requirements = run.step_artifact_requirements.get(task_id, [])
        if not requirements:
            return [], []

        resolved_artifact_ids: list[int] = []
        missing_requirements: list[dict[str, Any]] = []
        for requirement in requirements:
            from_task_ids = {int(value) for value in requirement.get("from_task_ids", [])}
            expected_type = requirement.get("artifact_type")
            expected_label = requirement.get("label")
            matched = [
                artifact
                for artifact in self._artifacts
                if artifact.run_id == run_id
                and artifact.producer_task_id in from_task_ids
                and (expected_type is None or artifact.artifact_type.value == expected_type)
                and self._artifact_has_label(artifact, expected_label)
            ]
            if not matched:
                missing_requirements.append(
                    {
                        "from_task_ids": sorted(from_task_ids),
                        "artifact_type": expected_type,
                        "label": expected_label,
                        "reason": "no matching artifacts",
                    }
                )
                return None, missing_requirements

            required_handoff_artifact_ids = self._required_handoff_artifact_ids(
                run_id=run_id,
                from_task_ids=from_task_ids,
            )
            matched_required_ids = [
                artifact.id
                for artifact in matched
                if artifact.id in required_handoff_artifact_ids
            ]
            if not matched_required_ids:
                missing_requirements.append(
                    {
                        "from_task_ids": sorted(from_task_ids),
                        "artifact_type": expected_type,
                        "label": expected_label,
                        "required_handoff_artifact_ids": sorted(required_handoff_artifact_ids),
                        "reason": "matching artifacts are not marked required in handoff",
                    }
                )
                return None, missing_requirements
            resolved_artifact_ids.extend(matched_required_ids)

        deduplicated: list[int] = []
        for artifact_id in resolved_artifact_ids:
            if artifact_id in deduplicated:
                continue
            deduplicated.append(artifact_id)
        return deduplicated, []

    def _required_handoff_artifact_ids(self, *, run_id: int, from_task_ids: set[int]) -> set[int]:
        required_artifact_ids: set[int] = set()
        for from_task_id in from_task_ids:
            handoff = self._handoffs.get(from_task_id)
            if handoff is None:
                continue
            if handoff.run_id != run_id:
                continue
            for artifact in handoff.artifacts:
                if artifact.is_required:
                    required_artifact_ids.add(artifact.artifact_id)
        return required_artifact_ids

    @staticmethod
    def _artifact_has_label(artifact: ArtifactRead, expected_label: str | None) -> bool:
        if expected_label is None:
            return True

        label_value = artifact.metadata.get("label")
        if isinstance(label_value, str) and label_value == expected_label:
            return True

        labels_value = artifact.metadata.get("labels")
        if isinstance(labels_value, list) and expected_label in labels_value:
            return True

        return False

    def _validate_role_skill_packs(self, skill_packs: list[str]) -> None:
        if not skill_packs:
            return
        known_pack_names = {record.name for record in self._skill_packs.values()}
        unknown = [value for value in skill_packs if value not in known_pack_names]
        if unknown:
            raise ValidationError(f"unknown skill packs: {', '.join(unknown)}")

    def _validate_skill_pack(self, *, name: str, skills: list[str]) -> None:
        if not name.strip():
            raise ValidationError("skill pack name must not be empty")
        if not skills:
            raise ValidationError("skill pack must include at least one skill")
        unknown_skills = [skill for skill in skills if skill not in self._skills_catalog]
        if unknown_skills:
            raise ValidationError(f"unknown skills in pack '{name}': {', '.join(unknown_skills)}")

    def _load_skills_catalog(self) -> set[str]:
        source_file = Path(__file__).resolve()
        docs_path: Path | None = None
        for base in source_file.parents:
            candidate = base / "docs" / "SKILLS_CATALOG.md"
            if candidate.exists():
                docs_path = candidate
                break
        if docs_path is None:
            return set()

        skills: set[str] = set()
        for line in docs_path.read_text(encoding="utf-8").splitlines():
            trimmed = line.strip()
            if not trimmed.startswith(tuple(str(index) + "." for index in range(1, 100))):
                continue
            if "`" not in trimmed:
                continue
            parts = trimmed.split("`")
            if len(parts) >= 3 and parts[1]:
                skills.add(parts[1])
        return skills

    def _normalize_shared_lock_paths(self, project_id: int, lock_paths: list[str]) -> list[str]:
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")

        root = Path(project.root_path).resolve()
        allowed_roots = [Path(value).resolve() for value in project.allowed_paths]
        normalized_paths: list[Path] = []

        for raw_path in lock_paths:
            candidate = Path(raw_path).resolve()
            if not self._is_same_or_under(root, candidate):
                raise ValidationError(f"lock path is outside project root: {candidate}")

            if allowed_roots and not any(self._is_same_or_under(allowed_root, candidate) for allowed_root in allowed_roots):
                raise ValidationError(f"lock path is outside allowed paths: {candidate}")

            normalized_paths.append(candidate)

        deduplicated: list[Path] = []
        for candidate in sorted(set(normalized_paths), key=lambda item: len(str(item))):
            if any(self._is_same_or_under(existing, candidate) for existing in deduplicated):
                continue
            deduplicated.append(candidate)

        return [str(path) for path in deduplicated]

    def _acquire_shared_workspace(
        self,
        *,
        task_id: int,
        project_id: int | None,
        lock_paths: list[str],
    ) -> RunnerWorkspaceContext:
        if project_id is None:
            raise ValidationError("shared-workspace task must define project_id")
        if not lock_paths:
            raise ValidationError("shared-workspace task must define lock_paths")

        normalized_paths = self._normalize_shared_lock_paths(project_id, lock_paths)
        conflict_reasons: list[str] = []

        for candidate in normalized_paths:
            candidate_path = Path(candidate)
            for locked_path, owner_task_id in self._path_locks.items():
                if owner_task_id == task_id:
                    continue
                locked_path_obj = Path(locked_path)
                if self._paths_overlap(candidate_path, locked_path_obj):
                    conflict_reasons.append(f"{candidate} locked by task {owner_task_id} ({locked_path})")

        if conflict_reasons:
            raise ConflictError(f"shared-workspace lock conflict: {'; '.join(conflict_reasons)}")

        for path in normalized_paths:
            self._path_locks[path] = task_id
        self._task_locks[task_id] = normalized_paths

        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")

        return RunnerWorkspaceContext(
            project_id=project.id,
            project_root=project.root_path,
            lock_paths=normalized_paths,
        )

    @staticmethod
    def _task_run_id(task_id: int, run_id: int | None) -> str:
        if run_id is None:
            return f"standalone:task-{task_id}"
        return f"run-{run_id}:task-{task_id}"

    def _build_handoff_context(self, *, run_id: int | None, task_id: int) -> list[TaskHandoffRead]:
        if run_id is None:
            return []
        run = self._workflow_runs.get(run_id)
        if run is None:
            return []
        dependency_task_ids = run.step_dependencies.get(task_id, [])
        context: list[TaskHandoffRead] = []
        for dependency_task_id in dependency_task_ids:
            handoff = self._handoffs.get(dependency_task_id)
            if handoff is None:
                continue
            if handoff.run_id != run_id:
                continue
            context.append(handoff)
        return context

    def _upsert_task_handoff(
        self,
        *,
        task_id: int,
        run_id: int | None,
        handoff: TaskHandoffPayload,
    ) -> TaskHandoffRead:
        known_artifacts_by_id = {artifact.id: artifact for artifact in self._artifacts}
        for artifact_ref in handoff.artifacts:
            artifact = known_artifacts_by_id.get(artifact_ref.artifact_id)
            if artifact is None:
                raise ValidationError(f"handoff artifact {artifact_ref.artifact_id} not found")
            if artifact.producer_task_id != task_id:
                raise ValidationError(
                    f"handoff artifact {artifact_ref.artifact_id} must be produced by task {task_id}"
                )
            if run_id is not None and artifact.run_id != run_id:
                raise ValidationError(
                    f"handoff artifact {artifact_ref.artifact_id} must belong to workflow run {run_id}"
                )

        now = self._utc_now()
        existing = self._handoffs.get(task_id)
        created_at = existing.created_at if existing is not None else now
        saved = TaskHandoffRead(
            task_id=task_id,
            run_id=run_id,
            summary=handoff.summary,
            details=handoff.details,
            next_actions=handoff.next_actions,
            open_questions=handoff.open_questions,
            artifacts=handoff.artifacts,
            created_at=created_at,
            updated_at=now,
        )
        self._handoffs[task_id] = saved
        self._append_event(
            event_type="task.handoff_published",
            run_id=run_id,
            task_id=task_id,
            payload={
                "summary": saved.summary,
                "details": saved.details,
                "next_actions": saved.next_actions,
                "open_questions": saved.open_questions,
                "artifacts": [artifact.model_dump() for artifact in saved.artifacts],
                "required_artifact_ids": [
                    artifact.artifact_id for artifact in saved.artifacts if artifact.is_required
                ],
            },
        )
        return saved

    def _build_isolated_session_identifiers(
        self,
        *,
        project_root: Path,
        task_id: int,
        run_id: int | None,
    ) -> tuple[Path, str]:
        run_segment = f"run-{run_id}" if run_id is not None else "standalone"
        worktree_path = project_root / ".multyagents" / "worktrees" / run_segment / f"task-{task_id}"
        git_branch = f"multyagents/{run_segment}/task-{task_id}"
        return worktree_path, git_branch

    def _acquire_isolated_workspace(
        self,
        *,
        task_id: int,
        run_id: int | None,
        project_id: int | None,
    ) -> RunnerWorkspaceContext:
        if project_id is None:
            raise ValidationError("isolated-worktree task must define project_id")
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")

        project_root = Path(project.root_path).resolve()
        worktree_path, git_branch = self._build_isolated_session_identifiers(
            project_root=project_root,
            task_id=task_id,
            run_id=run_id,
        )
        locked_worktree_owner = self._isolated_worktree_locks.get(str(worktree_path))
        if locked_worktree_owner is not None and locked_worktree_owner != task_id:
            raise ConflictError(
                f"isolated-worktree collision: worktree '{worktree_path}' is reserved by task {locked_worktree_owner}"
            )
        locked_branch_owner = self._isolated_branch_locks.get(git_branch)
        if locked_branch_owner is not None and locked_branch_owner != task_id:
            raise ConflictError(
                f"isolated-worktree collision: branch '{git_branch}' is reserved by task {locked_branch_owner}"
            )

        task_run_id = self._task_run_id(task_id, run_id)
        session = _IsolatedSessionRecord(
            task_id=task_id,
            run_id=run_id,
            task_run_id=task_run_id,
            project_id=project.id,
            project_root=str(project_root),
            worktree_path=str(worktree_path),
            git_branch=git_branch,
        )
        self._isolated_sessions[task_id] = session
        self._isolated_worktree_locks[session.worktree_path] = task_id
        self._isolated_branch_locks[session.git_branch] = task_id
        self._append_event(
            event_type="task.worktree_session_reserved",
            run_id=run_id,
            task_id=task_id,
            payload={
                "task_run_id": task_run_id,
                "worktree_path": session.worktree_path,
                "git_branch": session.git_branch,
            },
        )
        return RunnerWorkspaceContext(
            project_id=project.id,
            project_root=str(project_root),
            lock_paths=[],
            worktree_path=session.worktree_path,
            git_branch=session.git_branch,
        )

    def _release_isolated_session_internal(
        self,
        *,
        task_id: int,
        run_id: int | None,
        reason: str,
        cleanup_attempted: bool | None,
        cleanup_succeeded: bool | None,
        cleanup_message: str | None,
    ) -> _IsolatedSessionRecord | None:
        session = self._isolated_sessions.pop(task_id, None)
        if session is not None:
            if self._isolated_worktree_locks.get(session.worktree_path) == task_id:
                del self._isolated_worktree_locks[session.worktree_path]
            if self._isolated_branch_locks.get(session.git_branch) == task_id:
                del self._isolated_branch_locks[session.git_branch]

        audit = self._audits.get(task_id)
        if audit is not None and audit.execution_mode == ExecutionMode.ISOLATED_WORKTREE:
            has_cleanup_update = (
                cleanup_attempted is not None
                or cleanup_succeeded is not None
                or cleanup_message is not None
            )
            if cleanup_attempted is not None:
                audit.worktree_cleanup_attempted = cleanup_attempted
            if cleanup_succeeded is not None:
                audit.worktree_cleanup_succeeded = cleanup_succeeded
            if cleanup_message is not None:
                audit.worktree_cleanup_message = cleanup_message
            if has_cleanup_update:
                audit.worktree_cleanup_at = self._utc_now()
            self._audits[task_id] = audit

        if session is None:
            return None

        self._append_event(
            event_type="task.worktree_session_released",
            run_id=run_id if run_id is not None else session.run_id,
            task_id=task_id,
            payload={
                "task_run_id": session.task_run_id,
                "worktree_path": session.worktree_path,
                "git_branch": session.git_branch,
                "reason": reason,
                "cleanup_attempted": cleanup_attempted,
                "cleanup_succeeded": cleanup_succeeded,
                "cleanup_message": cleanup_message,
            },
        )
        return session

    def _build_isolated_workspace(self, *, task_id: int, project_id: int | None) -> RunnerWorkspaceContext:
        # Deprecated for new dispatch flow; retained for backward-compatible tests/helpers.
        return self._acquire_isolated_workspace(task_id=task_id, run_id=None, project_id=project_id)

    def _build_docker_workspace(self, *, project_id: int | None) -> RunnerWorkspaceContext:
        if project_id is None:
            raise ValidationError("docker-sandbox task must define project_id")
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")
        return RunnerWorkspaceContext(
            project_id=project.id,
            project_root=str(Path(project.root_path).resolve()),
            lock_paths=[],
        )

    def _build_docker_sandbox(self, *, project_id: int | None, sandbox: SandboxConfig | None) -> SandboxConfig:
        if project_id is None:
            raise ValidationError("docker-sandbox task must define project_id")
        if sandbox is None:
            raise ValidationError("docker-sandbox task must define sandbox config")
        project = self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")

        normalized_mounts = list(sandbox.mounts)
        if not normalized_mounts:
            default_source = project.allowed_paths[0] if project.allowed_paths else project.root_path
            normalized_mounts = [
                SandboxMount(
                    source=default_source,
                    target=sandbox.workdir,
                    read_only=False,
                )
            ]

        validated_mounts = self._validate_docker_mounts(project, normalized_mounts)
        return SandboxConfig(
            image=sandbox.image,
            command=sandbox.command,
            workdir=sandbox.workdir,
            env=sandbox.env,
            mounts=validated_mounts,
        )

    def _validate_docker_mounts(self, project: _ProjectRecord, mounts: list[SandboxMount]) -> list[SandboxMount]:
        root = Path(project.root_path).resolve()
        allowed_roots = [Path(value).resolve() for value in project.allowed_paths]
        validated: list[SandboxMount] = []

        for mount in mounts:
            source = Path(mount.source).resolve()
            if not self._is_same_or_under(root, source):
                raise ValidationError(f"sandbox mount source is outside project root: {source}")
            if allowed_roots and not any(self._is_same_or_under(allowed, source) for allowed in allowed_roots):
                raise ValidationError(f"sandbox mount source is outside allowed paths: {source}")
            validated.append(
                SandboxMount(
                    source=str(source),
                    target=mount.target,
                    read_only=mount.read_only,
                )
            )
        return validated

    def _approval_status_for_task(self, task_id: int) -> ApprovalStatus | None:
        approval_id = self._task_approval.get(task_id)
        if approval_id is None:
            return None
        approval = self._approvals.get(approval_id)
        if approval is None:
            return None
        return ApprovalStatus(approval.status)

    def _require_approval_ready(
        self,
        *,
        task_id: int,
        requires_approval: bool,
        run_id: int | None,
    ) -> ApprovalStatus | None:
        if not requires_approval:
            return None

        approval_id = self._task_approval.get(task_id)
        if approval_id is None:
            raise ConflictError(f"task {task_id} requires approval but approval record is missing")

        approval = self._approvals.get(approval_id)
        if approval is None:
            raise NotFoundError(f"approval {approval_id} not found")

        status = ApprovalStatus(approval.status)
        if status != ApprovalStatus.APPROVED:
            self._append_event(
                event_type="task.dispatch_blocked_by_approval",
                run_id=run_id,
                task_id=task_id,
                payload={
                    "approval_id": approval.id,
                    "status": status.value,
                },
            )
            raise ConflictError(f"task {task_id} requires approval; approval_id={approval.id} status={status.value}")

        return status

    def _create_pending_approval(self, task_id: int) -> _ApprovalRecord:
        approval_id = self._approval_seq
        self._approval_seq += 1
        record = _ApprovalRecord(
            id=approval_id,
            task_id=task_id,
            status=ApprovalStatus.PENDING.value,
            decided_by=None,
            comment=None,
        )
        self._approvals[approval_id] = record
        self._append_event(
            event_type="approval.pending",
            task_id=task_id,
            payload={"approval_id": approval_id},
        )
        return record

    def _set_approval_status(self, approval_id: int, *, status: str, actor: str | None, comment: str | None) -> ApprovalRead:
        record = self._approvals.get(approval_id)
        if record is None:
            raise NotFoundError(f"approval {approval_id} not found")

        updated = _ApprovalRecord(
            id=record.id,
            task_id=record.task_id,
            status=status,
            decided_by=actor,
            comment=comment,
        )
        self._approvals[approval_id] = updated

        run_id = self._task_latest_run.get(record.task_id)
        self._append_event(
            event_type=f"approval.{status}",
            run_id=run_id,
            task_id=record.task_id,
            payload={
                "approval_id": approval_id,
                "actor": actor,
                "comment": comment,
            },
        )
        self._persist_state()
        return self._to_approval_read(updated)

    def _release_task_locks_internal(self, *, task_id: int, run_id: int | None, emit_event: bool) -> list[str]:
        released_paths = self._task_locks.pop(task_id, [])
        for path in released_paths:
            if self._path_locks.get(path) == task_id:
                del self._path_locks[path]

        if emit_event:
            self._append_event(
                event_type="task.locks_released",
                run_id=run_id,
                task_id=task_id,
                payload={"released_paths": released_paths},
            )
        return released_paths

    def _evaluate_retry_for_failure(
        self,
        *,
        task_id: int,
        failure_status: str,
        message: str | None,
        exit_code: int | None,
        stdout: str | None,
        stderr: str | None,
    ) -> dict[str, Any]:
        category = self._classify_failure_category(
            failure_status=failure_status,
            message=message,
            stdout=stdout,
            stderr=stderr,
        )
        hint = self._recovery_hint_for_category(category)
        max_retries, retry_on = self._resolve_retry_policy(task_id)

        audit = self._audits.get(task_id)
        retry_attempt = 0
        if audit is not None:
            retry_attempt = audit.retry_attempts
            if category is not None:
                self._append_unique(audit.failure_categories, category)
            if hint is not None:
                self._append_unique(audit.failure_triage_hints, hint)

        retry_allowed = (
            audit is not None
            and category is not None
            and max_retries > 0
            and category in retry_on
            and retry_attempt < max_retries
        )

        retry_reason: str | None = None
        if retry_allowed:
            retry_attempt += 1
            retries_remaining = max_retries - retry_attempt
            retry_reason = f"retry scheduled after transient {category} failure ({retry_attempt}/{max_retries})"
            if message:
                retry_reason = f"{retry_reason}: {message}"
            if audit is not None:
                audit.retry_attempts = retry_attempt
                audit.last_retry_reason = retry_reason
                self._audits[task_id] = audit
        else:
            retries_remaining = max(max_retries - retry_attempt, 0)
            if audit is not None:
                if category is None:
                    audit.last_retry_reason = "retry policy skipped: failure category is not transient"
                elif max_retries <= 0:
                    audit.last_retry_reason = "retry policy skipped: max_retries=0"
                elif category not in retry_on:
                    audit.last_retry_reason = f"retry policy skipped: category '{category}' not in retry_on"
                elif retry_attempt >= max_retries:
                    audit.last_retry_reason = f"retry policy exhausted at {retry_attempt}/{max_retries}"
                self._audits[task_id] = audit

        return {
            "retry_scheduled": retry_allowed,
            "failure_category": category,
            "recovery_hint": hint,
            "retry_attempt": retry_attempt,
            "max_retries": max_retries,
            "retries_remaining": retries_remaining,
            "retry_reason": retry_reason,
            "exit_code": exit_code,
        }

    def _resolve_retry_policy(self, task_id: int) -> tuple[int, set[str]]:
        task = self._tasks.get(task_id)
        if task is None:
            return 0, set()
        role = self._roles.get(task.role_id)
        if role is None:
            return 0, set()

        retry_policy = role.execution_constraints.get("retry_policy")
        if not isinstance(retry_policy, dict):
            return 0, set()

        raw_max_retries = retry_policy.get("max_retries")
        if isinstance(raw_max_retries, bool):
            max_retries = 0
        elif isinstance(raw_max_retries, int):
            max_retries = raw_max_retries
        else:
            max_retries = 0
        max_retries = max(0, min(max_retries, 10))

        raw_retry_on = retry_policy.get("retry_on")
        retry_on: set[str] = set()
        if isinstance(raw_retry_on, list):
            for value in raw_retry_on:
                if not isinstance(value, str):
                    continue
                normalized = value.strip().lower()
                if normalized in {"network", "flaky-test", "runner-transient"}:
                    retry_on.add(normalized)
        return max_retries, retry_on

    @staticmethod
    def _classify_failure_category(
        *,
        failure_status: str,
        message: str | None,
        stdout: str | None,
        stderr: str | None,
    ) -> str | None:
        text_blob = " ".join([message or "", stdout or "", stderr or ""]).lower()
        if not text_blob and failure_status == TaskStatus.SUBMIT_FAILED.value:
            return "runner-transient"

        network_markers = (
            "timeout",
            "timed out",
            "connection refused",
            "connection reset",
            "network",
            "dns",
            "name or service not known",
            "temporary failure in name resolution",
            "503",
            "504",
            "502",
        )
        if any(marker in text_blob for marker in network_markers):
            return "network"

        flaky_markers = (
            "flaky",
            "nondeterministic",
            "race condition",
            "intermittent",
            "failed test",
            "assertionerror",
            "pytest",
        )
        if any(marker in text_blob for marker in flaky_markers):
            return "flaky-test"

        runner_transient_markers = (
            "runner submit failed",
            "runner unavailable",
            "runner busy",
            "temporary",
            "try again",
            "resource temporarily unavailable",
            "service unavailable",
        )
        if any(marker in text_blob for marker in runner_transient_markers):
            return "runner-transient"

        if failure_status == TaskStatus.SUBMIT_FAILED.value:
            return "runner-transient"
        return None

    @staticmethod
    def _recovery_hint_for_category(category: str | None) -> str | None:
        if category == "network":
            return "Network/timeout failure detected. Verify host-runner connectivity and retry."
        if category == "flaky-test":
            return "Flaky test signal detected. Re-run failing tests with focused logs before escalation."
        if category == "runner-transient":
            return "Runner transient failure detected. Verify runner health/capacity and retry."
        return None

    @staticmethod
    def _append_unique(values: list[str], candidate: str) -> None:
        if candidate not in values:
            values.append(candidate)

    def _recompute_workflow_run_status(self, run_id: int) -> None:
        run = self._workflow_runs.get(run_id)
        if run is None:
            return
        if run.status == WorkflowRunStatus.ABORTED.value:
            return

        statuses: list[str] = []
        for task_id in run.task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            statuses.append(task.status)

        if not statuses:
            return

        next_status = run.status
        event_type: str | None = None
        if all(status == TaskStatus.SUCCESS.value for status in statuses):
            next_status = WorkflowRunStatus.SUCCESS.value
            event_type = "workflow_run.succeeded"
        elif any(
            status in (TaskStatus.FAILED.value, TaskStatus.CANCELED.value, TaskStatus.SUBMIT_FAILED.value)
            for status in statuses
        ):
            next_status = WorkflowRunStatus.FAILED.value
            event_type = "workflow_run.failed"
        elif any(
            status
            in (
                TaskStatus.DISPATCHED.value,
                TaskStatus.QUEUED.value,
                TaskStatus.RUNNING.value,
                TaskStatus.CANCEL_REQUESTED.value,
            )
            for status in statuses
        ):
            next_status = WorkflowRunStatus.RUNNING.value
            event_type = "workflow_run.running"

        if next_status == run.status:
            return

        updated = _WorkflowRunRecord(
            id=run.id,
            workflow_template_id=run.workflow_template_id,
            task_ids=run.task_ids,
            status=next_status,
            initiated_by=run.initiated_by,
            created_at=run.created_at,
            updated_at=self._utc_now(),
            step_dependencies=run.step_dependencies,
            step_artifact_requirements=run.step_artifact_requirements,
        )
        self._workflow_runs[run_id] = updated
        if event_type is not None:
            self._append_event(
                event_type=event_type,
                run_id=run_id,
                payload={"status": next_status},
            )

    @staticmethod
    def _is_terminal_task_status(status: str) -> bool:
        return status in (
            TaskStatus.SUCCESS.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELED.value,
            TaskStatus.SUBMIT_FAILED.value,
        )

    def _set_workflow_run_status(self, run_id: int, status: WorkflowRunStatus, event_type: str) -> WorkflowRunRead:
        record = self._workflow_runs.get(run_id)
        if record is None:
            raise NotFoundError(f"workflow run {run_id} not found")

        if record.status == WorkflowRunStatus.ABORTED.value and status != WorkflowRunStatus.ABORTED:
            raise ConflictError(f"workflow run {run_id} is aborted")

        updated = _WorkflowRunRecord(
            id=record.id,
            workflow_template_id=record.workflow_template_id,
            task_ids=record.task_ids,
            status=status.value,
            initiated_by=record.initiated_by,
            created_at=record.created_at,
            updated_at=self._utc_now(),
            step_dependencies=record.step_dependencies,
            step_artifact_requirements=record.step_artifact_requirements,
        )
        self._workflow_runs[run_id] = updated
        self._append_event(
            event_type=event_type,
            run_id=run_id,
            payload={"status": status.value},
        )
        self._persist_state()
        return self._to_workflow_run_read(updated)

    def _append_event(
        self,
        *,
        event_type: str,
        run_id: int | None = None,
        task_id: int | None = None,
        producer_role: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> EventRead:
        event = EventRead(
            id=self._event_seq,
            event_type=event_type,
            run_id=run_id,
            task_id=task_id,
            producer_role=producer_role,
            payload=payload or {},
            created_at=self._utc_now(),
        )
        self._event_seq += 1
        self._events.append(event)
        if task_id is not None:
            audit = self._audits.get(task_id)
            if audit is not None:
                audit.recent_event_ids.append(event.id)
                if len(audit.recent_event_ids) > 200:
                    audit.recent_event_ids = audit.recent_event_ids[-200:]
                self._audits[task_id] = audit
        return event

    def _persist_state(self) -> None:
        if self._state_file is None:
            return

        snapshot = self._snapshot()
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self._state_file.with_name(f"{self._state_file.name}.tmp")
        tmp_file.write_text(json.dumps(snapshot, ensure_ascii=True, sort_keys=True), encoding="utf-8")
        tmp_file.replace(self._state_file)

    def _load_state(self) -> None:
        if self._state_file is None or not self._state_file.exists():
            return

        raw = self._state_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        self._projects = {
            int(key): _ProjectRecord(**value)
            for key, value in data.get("projects", {}).items()
        }
        self._skill_packs = {
            int(key): _SkillPackRecord(**value)
            for key, value in data.get("skill_packs", {}).items()
        }
        self._roles = {
            int(key): _RoleRecord(**value)
            for key, value in data.get("roles", {}).items()
        }
        self._tasks = {
            int(key): _TaskRecord(**value)
            for key, value in data.get("tasks", {}).items()
        }
        self._path_locks = {str(key): int(value) for key, value in data.get("path_locks", {}).items()}
        self._task_locks = {
            int(key): [str(item) for item in value]
            for key, value in data.get("task_locks", {}).items()
        }
        self._isolated_sessions = {
            int(key): _IsolatedSessionRecord(**value)
            for key, value in data.get("isolated_sessions", {}).items()
        }
        self._isolated_worktree_locks = {
            str(key): int(value) for key, value in data.get("isolated_worktree_locks", {}).items()
        }
        self._isolated_branch_locks = {
            str(key): int(value) for key, value in data.get("isolated_branch_locks", {}).items()
        }
        self._workflow_templates = {
            int(key): _WorkflowTemplateRecord(
                id=int(value["id"]),
                name=value["name"],
                project_id=value["project_id"],
                steps=[WorkflowStep(**step) for step in value["steps"]],
            )
            for key, value in data.get("workflow_templates", {}).items()
        }
        self._workflow_runs = {
            int(key): _WorkflowRunRecord(
                id=int(value["id"]),
                workflow_template_id=value.get("workflow_template_id"),
                task_ids=[int(task_id) for task_id in value.get("task_ids", [])],
                status=value["status"],
                initiated_by=value.get("initiated_by"),
                created_at=value["created_at"],
                updated_at=value["updated_at"],
                step_dependencies={
                    int(task_id): [int(dep_task_id) for dep_task_id in dep_task_ids]
                    for task_id, dep_task_ids in value.get("step_dependencies", {}).items()
                },
                step_artifact_requirements={
                    int(task_id): [dict(requirement) for requirement in requirements]
                    for task_id, requirements in value.get("step_artifact_requirements", {}).items()
                },
            )
            for key, value in data.get("workflow_runs", {}).items()
        }
        self._task_latest_run = {int(key): int(value) for key, value in data.get("task_latest_run", {}).items()}
        self._approvals = {
            int(key): _ApprovalRecord(**value)
            for key, value in data.get("approvals", {}).items()
        }
        self._task_approval = {int(key): int(value) for key, value in data.get("task_approval", {}).items()}
        self._audits = {
            int(key): TaskAudit(**value)
            for key, value in data.get("audits", {}).items()
        }
        self._handoffs = {
            int(key): TaskHandoffRead(**value)
            for key, value in data.get("handoffs", {}).items()
        }
        self._events = [EventRead(**event) for event in data.get("events", [])]
        self._artifacts = [ArtifactRead(**artifact) for artifact in data.get("artifacts", [])]

        sequences = data.get("sequences", {})
        self._project_seq = int(sequences.get("project_seq", 1))
        self._skill_pack_seq = int(sequences.get("skill_pack_seq", 1))
        self._role_seq = int(sequences.get("role_seq", 1))
        self._task_seq = int(sequences.get("task_seq", 1))
        self._workflow_template_seq = int(sequences.get("workflow_template_seq", 1))
        self._workflow_run_seq = int(sequences.get("workflow_run_seq", 1))
        self._approval_seq = int(sequences.get("approval_seq", 1))
        self._event_seq = int(sequences.get("event_seq", 1))
        self._artifact_seq = int(sequences.get("artifact_seq", 1))

    def _snapshot(self) -> dict[str, Any]:
        return {
            "projects": {str(key): value.__dict__ for key, value in self._projects.items()},
            "skill_packs": {str(key): value.__dict__ for key, value in self._skill_packs.items()},
            "roles": {str(key): value.__dict__ for key, value in self._roles.items()},
            "tasks": {str(key): value.__dict__ for key, value in self._tasks.items()},
            "path_locks": self._path_locks,
            "task_locks": {str(key): value for key, value in self._task_locks.items()},
            "isolated_sessions": {str(key): value.__dict__ for key, value in self._isolated_sessions.items()},
            "isolated_worktree_locks": self._isolated_worktree_locks,
            "isolated_branch_locks": self._isolated_branch_locks,
            "workflow_templates": {
                str(key): {
                    "id": value.id,
                    "name": value.name,
                    "project_id": value.project_id,
                    "steps": [step.model_dump() for step in value.steps],
                }
                for key, value in self._workflow_templates.items()
            },
            "workflow_runs": {str(key): value.__dict__ for key, value in self._workflow_runs.items()},
            "task_latest_run": {str(key): value for key, value in self._task_latest_run.items()},
            "approvals": {str(key): value.__dict__ for key, value in self._approvals.items()},
            "task_approval": {str(key): value for key, value in self._task_approval.items()},
            "audits": {str(key): value.model_dump() for key, value in self._audits.items()},
            "handoffs": {str(key): value.model_dump() for key, value in self._handoffs.items()},
            "events": [event.model_dump() for event in self._events],
            "artifacts": [artifact.model_dump() for artifact in self._artifacts],
            "sequences": {
                "project_seq": self._project_seq,
                "skill_pack_seq": self._skill_pack_seq,
                "role_seq": self._role_seq,
                "task_seq": self._task_seq,
                "workflow_template_seq": self._workflow_template_seq,
                "workflow_run_seq": self._workflow_run_seq,
                "approval_seq": self._approval_seq,
                "event_seq": self._event_seq,
                "artifact_seq": self._artifact_seq,
            },
        }

    @staticmethod
    def _to_approval_read(record: _ApprovalRecord) -> ApprovalRead:
        return ApprovalRead(
            id=record.id,
            task_id=record.task_id,
            status=record.status,
            decided_by=record.decided_by,
            comment=record.comment,
        )

    def _to_skill_pack_read(self, record: _SkillPackRecord) -> SkillPackRead:
        used_by_role_ids: list[int] = []
        for role in self._roles.values():
            if record.name in role.skill_packs:
                used_by_role_ids.append(role.id)
        return SkillPackRead(
            id=record.id,
            name=record.name,
            skills=record.skills,
            used_by_role_ids=used_by_role_ids,
        )

    def _to_task_read(self, record: _TaskRecord) -> TaskRead:
        sandbox = SandboxConfig(**record.sandbox) if record.sandbox is not None else None
        quality_gate_policy = self._task_quality_gate_policy(record)
        quality_gate_summary = self._evaluate_task_quality_gates(record, policy=quality_gate_policy)
        failure_category, failure_triage_hints, suggested_next_actions = self._triage_for_task_record(record)
        return TaskRead(
            id=record.id,
            role_id=record.role_id,
            title=record.title,
            context7_mode=record.context7_mode,
            execution_mode=record.execution_mode,
            status=record.status,
            requires_approval=record.requires_approval,
            project_id=record.project_id,
            lock_paths=record.lock_paths,
            sandbox=sandbox,
            runner_message=record.runner_message,
            started_at=record.started_at,
            finished_at=record.finished_at,
            exit_code=record.exit_code,
            failure_category=failure_category,
            failure_triage_hints=failure_triage_hints,
            suggested_next_actions=suggested_next_actions,
            quality_gate_policy=quality_gate_policy,
            quality_gate_summary=quality_gate_summary,
        )

    def _task_quality_gate_policy(self, record: _TaskRecord) -> QualityGatePolicy:
        raw_policy = record.quality_gate_policy
        if raw_policy:
            try:
                return QualityGatePolicy(**raw_policy)
            except Exception:
                pass
        return QualityGatePolicy(
            required_checks=[
                {
                    "check": QualityGateCheckId.TASK_STATUS.value,
                    "required": True,
                    "severity": QualityGateSeverity.BLOCKER.value,
                }
            ]
        )

    def _evaluate_task_quality_gates(self, record: _TaskRecord, *, policy: QualityGatePolicy) -> QualityGateSummary:
        results: list[QualityGateCheckResult] = []
        for check_policy in policy.required_checks:
            check_name = check_policy.check.value if isinstance(check_policy.check, Enum) else str(check_policy.check)
            severity = check_policy.severity
            required = check_policy.required
            status = QualityGateCheckStatus.FAIL
            message = "unknown quality gate check"
            details: dict[str, Any] = {"check": check_name}

            if check_name == QualityGateCheckId.TASK_STATUS.value:
                details["task_status"] = record.status
                if record.status == TaskStatus.SUCCESS.value:
                    status = QualityGateCheckStatus.PASS
                    message = "task completed successfully"
                elif self._is_terminal_task_status(record.status):
                    status = QualityGateCheckStatus.FAIL
                    message = f"task completed with terminal status '{record.status}'"
                else:
                    status = QualityGateCheckStatus.PENDING
                    message = "task is still in progress"
            elif check_name == QualityGateCheckId.APPROVAL_STATUS.value:
                approval_status = self._approval_status_for_task(record.id)
                details["task_requires_approval"] = record.requires_approval
                details["approval_status"] = approval_status.value if approval_status is not None else None
                if not record.requires_approval:
                    status = QualityGateCheckStatus.SKIPPED
                    message = "approval gate is not enabled for this task"
                elif approval_status == ApprovalStatus.APPROVED:
                    status = QualityGateCheckStatus.PASS
                    message = "approval granted"
                elif approval_status == ApprovalStatus.REJECTED:
                    status = QualityGateCheckStatus.FAIL
                    message = "approval rejected"
                else:
                    status = QualityGateCheckStatus.PENDING
                    message = "approval is pending"
            elif check_name == QualityGateCheckId.HANDOFF_PRESENT.value:
                handoff = self._handoffs.get(record.id)
                has_handoff = handoff is not None and handoff.summary.strip() != ""
                details["has_handoff"] = has_handoff
                if has_handoff:
                    status = QualityGateCheckStatus.PASS
                    message = "handoff payload is published"
                elif self._is_terminal_task_status(record.status):
                    status = QualityGateCheckStatus.FAIL
                    message = "terminal task is missing handoff payload"
                else:
                    status = QualityGateCheckStatus.PENDING
                    message = "handoff payload has not been published yet"
            elif check_name == QualityGateCheckId.REQUIRED_ARTIFACTS_PRESENT.value:
                handoff = self._handoffs.get(record.id)
                if handoff is None:
                    details["required_artifact_ids"] = []
                    if self._is_terminal_task_status(record.status):
                        status = QualityGateCheckStatus.FAIL
                        message = "terminal task has no handoff artifact references"
                    else:
                        status = QualityGateCheckStatus.PENDING
                        message = "handoff artifacts are not available yet"
                else:
                    required_artifact_ids = [
                        artifact.artifact_id for artifact in handoff.artifacts if artifact.is_required
                    ]
                    details["required_artifact_ids"] = required_artifact_ids
                    if not required_artifact_ids:
                        status = QualityGateCheckStatus.PASS
                        message = "no required handoff artifacts declared"
                    else:
                        artifacts_by_id = {artifact.id: artifact for artifact in self._artifacts}
                        missing_artifact_ids: list[int] = []
                        invalid_producer_ids: list[int] = []
                        invalid_run_ids: list[int] = []
                        for artifact_id in required_artifact_ids:
                            artifact = artifacts_by_id.get(artifact_id)
                            if artifact is None:
                                missing_artifact_ids.append(artifact_id)
                                continue
                            if artifact.producer_task_id != record.id:
                                invalid_producer_ids.append(artifact_id)
                                continue
                            if handoff.run_id is not None and artifact.run_id != handoff.run_id:
                                invalid_run_ids.append(artifact_id)

                        details["missing_artifact_ids"] = missing_artifact_ids
                        details["invalid_producer_ids"] = invalid_producer_ids
                        details["invalid_run_ids"] = invalid_run_ids
                        if missing_artifact_ids or invalid_producer_ids or invalid_run_ids:
                            status = QualityGateCheckStatus.FAIL
                            message = "required handoff artifacts are missing or invalid"
                        else:
                            status = QualityGateCheckStatus.PASS
                            message = "required handoff artifacts are available"
            else:
                status = QualityGateCheckStatus.FAIL
                message = f"unknown quality gate check '{check_name}'"

            blocker = (
                status == QualityGateCheckStatus.FAIL
                and required
                and severity == QualityGateSeverity.BLOCKER
            )
            results.append(
                QualityGateCheckResult(
                    check=check_name,
                    status=status,
                    severity=severity,
                    required=required,
                    blocker=blocker,
                    message=message,
                    details=details,
                )
            )

        if not results:
            return QualityGateSummary()

        passed_checks = sum(1 for item in results if item.status == QualityGateCheckStatus.PASS)
        failed_checks = sum(1 for item in results if item.status == QualityGateCheckStatus.FAIL)
        pending_checks = sum(1 for item in results if item.status == QualityGateCheckStatus.PENDING)
        skipped_checks = sum(1 for item in results if item.status == QualityGateCheckStatus.SKIPPED)
        blocker_failures = sum(1 for item in results if item.blocker)
        warning_failures = sum(
            1
            for item in results
            if item.status == QualityGateCheckStatus.FAIL and not item.blocker
        )

        if blocker_failures > 0:
            summary_status = QualityGateSummaryStatus.FAIL
            summary_text = f"{blocker_failures} blocker gate(s) failed."
        elif pending_checks > 0:
            summary_status = QualityGateSummaryStatus.PENDING
            summary_text = f"{passed_checks}/{len(results)} checks passed, {pending_checks} pending."
        elif warning_failures > 0:
            summary_status = QualityGateSummaryStatus.PASS
            summary_text = f"Passed with {warning_failures} warning gate failure(s)."
        else:
            summary_status = QualityGateSummaryStatus.PASS
            summary_text = "All quality gates passed."

        return QualityGateSummary(
            status=summary_status,
            summary_text=summary_text,
            total_checks=len(results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            pending_checks=pending_checks,
            skipped_checks=skipped_checks,
            blocker_failures=blocker_failures,
            warning_failures=warning_failures,
            checks=results,
        )

    @staticmethod
    def _parse_timestamp(raw: str | None) -> datetime | None:
        if raw is None:
            return None
        candidate = raw.strip()
        if not candidate:
            return None
        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    @classmethod
    def _duration_ms(
        cls,
        *,
        started_at: str | None,
        finished_at: str | None,
        fallback_end: datetime | None = None,
    ) -> int | None:
        started = cls._parse_timestamp(started_at)
        if started is None:
            return None
        finished = cls._parse_timestamp(finished_at) if finished_at is not None else fallback_end
        if finished is None or finished < started:
            return None
        return int((finished - started).total_seconds() * 1000)

    def _dispatch_attempts_by_task_id(self, run_id: int) -> dict[int, int]:
        attempts: dict[int, int] = {}
        for event in self._events:
            if event.run_id != run_id:
                continue
            if event.event_type != "task.dispatched" or event.task_id is None:
                continue
            attempts[event.task_id] = attempts.get(event.task_id, 0) + 1
        return attempts

    def _build_workflow_run_metrics(
        self,
        record: _WorkflowRunRecord,
    ) -> tuple[int | None, float, int, list[WorkflowRunRoleMetric]]:
        task_records = [self._tasks[task_id] for task_id in record.task_ids if task_id in self._tasks]
        if not task_records:
            return None, 0.0, 0, []

        updated_at = self._parse_timestamp(record.updated_at)
        dispatch_attempts = self._dispatch_attempts_by_task_id(record.id)
        retries_total = sum(max(0, attempts - 1) for attempts in dispatch_attempts.values())

        successful_tasks = sum(1 for task in task_records if task.status == TaskStatus.SUCCESS.value)
        success_rate = round((successful_tasks / len(task_records)) * 100, 2)

        started_times = [self._parse_timestamp(task.started_at) for task in task_records]
        start_candidates = [item for item in started_times if item is not None]
        end_candidates = [self._parse_timestamp(task.finished_at) for task in task_records if task.finished_at is not None]
        if updated_at is not None and any(task.started_at is not None and task.finished_at is None for task in task_records):
            end_candidates.append(updated_at)
        end_candidates = [item for item in end_candidates if item is not None]
        duration_ms: int | None = None
        if start_candidates and end_candidates:
            started = min(start_candidates)
            finished = max(end_candidates)
            if finished >= started:
                duration_ms = int((finished - started).total_seconds() * 1000)

        failed_statuses = {
            TaskStatus.FAILED.value,
            TaskStatus.CANCELED.value,
            TaskStatus.SUBMIT_FAILED.value,
        }
        role_aggregate: dict[int, dict[str, int]] = {}
        for task in task_records:
            aggregate = role_aggregate.setdefault(
                task.role_id,
                {
                    "task_count": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                    "throughput_tasks": 0,
                    "retries_total": 0,
                    "duration_ms_total": 0,
                    "duration_samples": 0,
                },
            )
            aggregate["task_count"] += 1
            if task.status == TaskStatus.SUCCESS.value:
                aggregate["successful_tasks"] += 1
                aggregate["throughput_tasks"] += 1
            elif task.status in failed_statuses:
                aggregate["failed_tasks"] += 1
                aggregate["throughput_tasks"] += 1
            aggregate["retries_total"] += max(0, dispatch_attempts.get(task.id, 0) - 1)

            task_duration_ms = self._duration_ms(
                started_at=task.started_at,
                finished_at=task.finished_at,
                fallback_end=updated_at if task.finished_at is None else None,
            )
            if task_duration_ms is not None:
                aggregate["duration_ms_total"] += task_duration_ms
                aggregate["duration_samples"] += 1

        per_role: list[WorkflowRunRoleMetric] = []
        for role_id in sorted(role_aggregate):
            aggregate = role_aggregate[role_id]
            role_success_rate = round((aggregate["successful_tasks"] / aggregate["task_count"]) * 100, 2)
            per_role.append(
                WorkflowRunRoleMetric(
                    role_id=role_id,
                    task_count=aggregate["task_count"],
                    successful_tasks=aggregate["successful_tasks"],
                    failed_tasks=aggregate["failed_tasks"],
                    throughput_tasks=aggregate["throughput_tasks"],
                    success_rate=role_success_rate,
                    retries_total=aggregate["retries_total"],
                    duration_ms=aggregate["duration_ms_total"] if aggregate["duration_samples"] > 0 else None,
                )
            )

        return duration_ms, success_rate, retries_total, per_role

    def _to_workflow_run_read(self, record: _WorkflowRunRecord) -> WorkflowRunRead:
        retry_summary, retry_categories, retry_hints = self._build_workflow_retry_surface(record)
        triage_categories, triage_hints, suggested_next_actions = self._triage_for_run_record(record)
        duration_ms, success_rate, retries_total, per_role = self._build_workflow_run_metrics(record)
        quality_gate_summary = self._build_workflow_run_quality_gate_summary(record)

        failure_categories = list(retry_categories)
        for category in triage_categories:
            self._append_unique(failure_categories, category)

        failure_triage_hints = list(retry_hints)
        for hint in triage_hints:
            self._append_unique(failure_triage_hints, hint)

        return WorkflowRunRead(
            id=record.id,
            workflow_template_id=record.workflow_template_id,
            task_ids=record.task_ids,
            status=record.status,
            initiated_by=record.initiated_by,
            created_at=record.created_at,
            updated_at=record.updated_at,
            retry_summary=retry_summary,
            failure_categories=failure_categories,
            failure_triage_hints=failure_triage_hints,
            suggested_next_actions=suggested_next_actions,
            duration_ms=duration_ms,
            success_rate=success_rate,
            retries_total=retries_total,
            per_role=per_role,
            quality_gate_summary=quality_gate_summary,
        )

    def _build_workflow_run_quality_gate_summary(self, record: _WorkflowRunRecord) -> QualityGateRunSummary:
        if not record.task_ids:
            return QualityGateRunSummary()

        total_tasks = 0
        passing_tasks = 0
        failing_tasks = 0
        pending_tasks = 0
        not_configured_tasks = 0
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        pending_checks = 0
        skipped_checks = 0
        blocker_failures = 0
        warning_failures = 0

        for task_id in record.task_ids:
            task_record = self._tasks.get(task_id)
            if task_record is None:
                continue
            total_tasks += 1
            task_summary = self._evaluate_task_quality_gates(
                task_record,
                policy=self._task_quality_gate_policy(task_record),
            )

            if task_summary.status == QualityGateSummaryStatus.PASS:
                passing_tasks += 1
            elif task_summary.status == QualityGateSummaryStatus.FAIL:
                failing_tasks += 1
            elif task_summary.status == QualityGateSummaryStatus.PENDING:
                pending_tasks += 1
            else:
                not_configured_tasks += 1

            total_checks += task_summary.total_checks
            passed_checks += task_summary.passed_checks
            failed_checks += task_summary.failed_checks
            pending_checks += task_summary.pending_checks
            skipped_checks += task_summary.skipped_checks
            blocker_failures += task_summary.blocker_failures
            warning_failures += task_summary.warning_failures

        if total_tasks == 0:
            return QualityGateRunSummary()
        if blocker_failures > 0:
            status = QualityGateSummaryStatus.FAIL
            summary_text = (
                f"{failing_tasks} task(s) have blocker gate failures "
                f"({blocker_failures} blocker check failure(s))."
            )
        elif pending_checks > 0 or pending_tasks > 0:
            status = QualityGateSummaryStatus.PENDING
            summary_text = (
                f"{passing_tasks}/{total_tasks} task(s) currently pass; "
                f"{pending_tasks} task(s) still pending quality checks."
            )
        elif total_checks == 0:
            status = QualityGateSummaryStatus.NOT_CONFIGURED
            summary_text = "No quality gates configured for tasks in this run."
        elif warning_failures > 0:
            status = QualityGateSummaryStatus.PASS
            summary_text = (
                f"Run passed blocker gates with {warning_failures} warning check failure(s)."
            )
        else:
            status = QualityGateSummaryStatus.PASS
            summary_text = "Run quality gates passed."

        return QualityGateRunSummary(
            status=status,
            summary_text=summary_text,
            total_tasks=total_tasks,
            passing_tasks=passing_tasks,
            failing_tasks=failing_tasks,
            pending_tasks=pending_tasks,
            not_configured_tasks=not_configured_tasks,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            pending_checks=pending_checks,
            skipped_checks=skipped_checks,
            blocker_failures=blocker_failures,
            warning_failures=warning_failures,
        )

    def _build_workflow_retry_surface(
        self, record: _WorkflowRunRecord
    ) -> tuple[dict[str, Any], list[str], list[str]]:
        total_retries = 0
        retried_task_ids: list[int] = []
        exhausted_task_ids: list[int] = []
        failure_categories: list[str] = []
        failure_triage_hints: list[str] = []

        for task_id in record.task_ids:
            audit = self._audits.get(task_id)
            if audit is None:
                continue
            if audit.retry_attempts > 0:
                total_retries += audit.retry_attempts
                retried_task_ids.append(task_id)
            for category in audit.failure_categories:
                self._append_unique(failure_categories, category)
            for hint in audit.failure_triage_hints:
                self._append_unique(failure_triage_hints, hint)

            max_retries, _retry_on = self._resolve_retry_policy(task_id)
            task = self._tasks.get(task_id)
            if (
                task is not None
                and task.status in (TaskStatus.FAILED.value, TaskStatus.SUBMIT_FAILED.value)
                and max_retries > 0
                and audit.retry_attempts >= max_retries
            ):
                exhausted_task_ids.append(task_id)

        if exhausted_task_ids:
            self._append_unique(
                failure_triage_hints,
                "Retry budget exhausted for one or more tasks. Manual intervention is required.",
            )

        retry_summary: dict[str, Any] = {
            "total_retries": total_retries,
            "retried_task_ids": retried_task_ids,
        }
        if exhausted_task_ids:
            retry_summary["exhausted_task_ids"] = exhausted_task_ids

        return retry_summary, failure_categories, failure_triage_hints

    def _triage_for_run_record(self, record: _WorkflowRunRecord) -> tuple[list[str], list[str], list[str]]:
        if record.status not in (WorkflowRunStatus.FAILED.value, WorkflowRunStatus.ABORTED.value):
            return [], [], []

        categories: list[str] = []
        hints: list[str] = []
        actions: list[str] = []

        for task_id in record.task_ids:
            task = self._tasks.get(task_id)
            if task is None:
                continue
            failure_category, task_hints, task_actions = self._triage_for_task_record(task)
            if failure_category is not None:
                categories.append(failure_category)
            hints.extend(task_hints)
            actions.extend(task_actions)

        if record.status == WorkflowRunStatus.ABORTED.value and not categories:
            categories.append("run-aborted")
            hints.append("Run was aborted by operator action before successful completion.")
            actions.append("Review the latest timeline events and decide whether to resume or start a new run.")

        return (
            self._dedupe_strings(categories),
            self._dedupe_strings(hints),
            self._dedupe_strings(actions),
        )

    def _triage_for_task_record(self, record: _TaskRecord) -> tuple[str | None, list[str], list[str]]:
        if record.status not in (
            TaskStatus.FAILED.value,
            TaskStatus.CANCELED.value,
            TaskStatus.SUBMIT_FAILED.value,
        ):
            return None, [], []

        message = (record.runner_message or "").strip()
        signal = self._task_failure_signal_text(record)
        category = "unknown"

        if record.status == TaskStatus.SUBMIT_FAILED.value:
            category = "runner-submit"
        elif record.status == TaskStatus.CANCELED.value:
            category = "canceled"
        elif self._contains_any(
            signal,
            (
                "timeout",
                "timed out",
                "connection refused",
                "connection reset",
                "network",
                "dns",
                "econn",
                "temporary failure",
                "host runner",
                "unreachable",
            ),
        ):
            category = "network"
        elif self._contains_any(
            signal,
            (
                "permission denied",
                "not permitted",
                "access denied",
                "unauthorized",
                "forbidden",
                "read-only file system",
            ),
        ):
            category = "permission"
        elif record.execution_mode == ExecutionMode.ISOLATED_WORKTREE.value and self._contains_any(
            signal,
            (
                "worktree",
                "git",
                "branch",
                "checkout",
                "merge",
                "rebase",
                "fatal:",
            ),
        ):
            category = "workspace-git"
        elif record.execution_mode == ExecutionMode.DOCKER_SANDBOX.value and self._contains_any(
            signal,
            (
                "docker",
                "container",
                "sandbox",
                "image",
            ),
        ):
            category = "sandbox"
        elif self._contains_any(
            signal,
            (
                "assertion",
                "test failed",
                "failed test",
                "pytest",
                "unit test",
                "integration test",
            ),
        ):
            category = "test-regression"
        elif self._contains_any(
            signal,
            (
                "command not found",
                "no module named",
                "module not found",
                "cannot find module",
                "no such file or directory",
                "package",
                "dependency",
            ),
        ):
            category = "dependency"
        elif record.execution_mode == ExecutionMode.DOCKER_SANDBOX.value:
            category = "sandbox"
        elif record.execution_mode == ExecutionMode.ISOLATED_WORKTREE.value:
            category = "workspace-git"

        if category == "runner-submit":
            return (
                category,
                ["Runner submission failed before task execution started."],
                [
                    "Check host-runner health and API-to-runner connectivity.",
                    "Retry task dispatch after runner endpoint is healthy.",
                ],
            )
        if category == "canceled":
            return (
                category,
                ["Task was canceled before completion."],
                [
                    "Confirm whether cancellation was expected or accidental.",
                    "Re-dispatch the task if the run should continue.",
                ],
            )
        if category == "network":
            return (
                category,
                ["Network/timeout failure detected. Verify runner connectivity and callback delivery."],
                [
                    "Validate HOST_RUNNER_URL and callback base URL reachability.",
                    "Retry the failed task once connectivity is restored.",
                ],
            )
        if category == "permission":
            return (
                category,
                ["Permission or policy denial detected during execution."],
                [
                    "Review project path policy and role tool constraints for this task.",
                    "Adjust permissions/policy and re-run the task.",
                ],
            )
        if category == "workspace-git":
            return (
                category,
                ["Isolated worktree or git operation failed during task execution."],
                [
                    "Inspect task audit worktree cleanup fields and recent worktree events.",
                    "Resolve git/worktree conflicts, then retry the task.",
                ],
            )
        if category == "sandbox":
            return (
                category,
                ["Docker sandbox runtime failure detected."],
                [
                    "Verify sandbox image, command, mounts, and container runtime health.",
                    "Re-run the task after fixing sandbox configuration or environment.",
                ],
            )
        if category == "test-regression":
            return (
                category,
                ["Task failed due to test/regression signals in runner output."],
                [
                    "Inspect stderr/stdout for failing assertions and stack traces.",
                    "Patch the implementation and re-run targeted tests before retry.",
                ],
            )
        if category == "dependency":
            return (
                category,
                ["Missing dependency or command detected in execution environment."],
                [
                    "Install or provision the missing dependency/tooling in task environment.",
                    "Retry after dependency validation passes.",
                ],
            )

        generic_hint = "Task failed without a recognized failure signature."
        if message:
            generic_hint = f"Task failed: {message}"
        return (
            category,
            [generic_hint],
            [
                "Inspect task audit, lifecycle events, and runner logs for root cause.",
                "Apply a fix or rollback and re-dispatch the task.",
            ],
        )

    def _task_failure_signal_text(self, record: _TaskRecord) -> str:
        audit = self._audits.get(record.id)
        parts = [
            record.runner_message or "",
            record.stderr or "",
            record.stdout or "",
            audit.sandbox_error if audit is not None and audit.sandbox_error is not None else "",
            audit.worktree_cleanup_message
            if audit is not None and audit.worktree_cleanup_message is not None
            else "",
        ]
        return " ".join(part.strip().lower() for part in parts if part and part.strip())

    @staticmethod
    def _contains_any(signal: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in signal for keyword in keywords)

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        deduped: list[str] = []
        for value in values:
            if value not in deduped:
                deduped.append(value)
        return deduped

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_same_or_under(base: Path, candidate: Path) -> bool:
        return candidate == base or base in candidate.parents

    @classmethod
    def _paths_overlap(cls, left: Path, right: Path) -> bool:
        return cls._is_same_or_under(left, right) or cls._is_same_or_under(right, left)
