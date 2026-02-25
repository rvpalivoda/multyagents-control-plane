from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multyagents_api.context_policy import resolve_context7_enabled
from multyagents_api.schemas import (
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
    TaskCreate,
    TaskRead,
    TaskStatus,
    WorkflowRunCreate,
    WorkflowRunRead,
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
            step_to_task_id: dict[str, int] = {}
            for step in template.steps:
                created = self.create_task(
                    TaskCreate(
                        role_id=step.role_id,
                        title=step.title,
                        context7_mode=Context7Mode.INHERIT,
                        execution_mode=ExecutionMode.NO_WORKSPACE,
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
                consumed_artifact_ids = self._resolve_handoff_artifacts(run_id=run.id, task_id=task_id)
                if consumed_artifact_ids is None:
                    artifact_blocked = True
                    continue
                return task_id, None, consumed_artifact_ids
            dependency_blocked = True

        if dependency_blocked:
            return None, "dependencies not satisfied", []
        if artifact_blocked:
            return None, "artifacts not satisfied", []
        return None, "no ready tasks", []

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
        )

        if consumed_artifact_ids is None:
            consumed_artifact_ids = []

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
            consumed_artifact_ids=consumed_artifact_ids,
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
        if is_terminal:
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

    def _resolve_handoff_artifacts(self, *, run_id: int, task_id: int) -> list[int] | None:
        run = self._workflow_runs.get(run_id)
        if run is None:
            raise NotFoundError(f"workflow run {run_id} not found")
        requirements = run.step_artifact_requirements.get(task_id, [])
        if not requirements:
            return []

        resolved_artifact_ids: list[int] = []
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
                return None
            resolved_artifact_ids.extend(artifact.id for artifact in matched)

        deduplicated: list[int] = []
        for artifact_id in resolved_artifact_ids:
            if artifact_id in deduplicated:
                continue
            deduplicated.append(artifact_id)
        return deduplicated

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

    @staticmethod
    def _to_task_read(record: _TaskRecord) -> TaskRead:
        sandbox = SandboxConfig(**record.sandbox) if record.sandbox is not None else None
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
        )

    @staticmethod
    def _to_workflow_run_read(record: _WorkflowRunRecord) -> WorkflowRunRead:
        return WorkflowRunRead(
            id=record.id,
            workflow_template_id=record.workflow_template_id,
            task_ids=record.task_ids,
            status=record.status,
            initiated_by=record.initiated_by,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_same_or_under(base: Path, candidate: Path) -> bool:
        return candidate == base or base in candidate.parents

    @classmethod
    def _paths_overlap(cls, left: Path, right: Path) -> bool:
        return cls._is_same_or_under(left, right) or cls._is_same_or_under(right, left)
