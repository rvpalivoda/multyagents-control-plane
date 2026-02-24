import { FormEvent, useEffect, useMemo, useState } from "react";
import type {
  ApprovalStatus,
  Context7Mode,
  EventRead,
  ExecutionMode,
  RoleRead,
  TaskAudit,
  TaskRead,
  WorkflowRunRead
} from "../../../packages/contracts/ts/context7";

type DispatchResult = {
  resolved_context7_enabled: boolean;
};

type WorkflowRunDispatchReadyResponse = {
  run_id: number;
  dispatched: boolean;
  task_id: number | null;
  reason: string | null;
  dispatch: DispatchResult | null;
};

type WorkflowStep = {
  step_id: string;
  role_id: number;
  title: string;
  depends_on: string[];
};

type WorkflowTemplateRead = {
  id: number;
  name: string;
  project_id: number | null;
  steps: WorkflowStep[];
};

type ProjectRead = {
  id: number;
  name: string;
  root_path: string;
  allowed_paths: string[];
};

type SkillPackRead = {
  id: number;
  name: string;
  skills: string[];
  used_by_role_ids: number[];
};

type ApprovalRead = {
  id: number;
  task_id: number;
  status: ApprovalStatus;
  decided_by: string | null;
  comment: string | null;
};

type UiTab = "overview" | "projects" | "roles" | "skills" | "workflows" | "runs" | "tasks" | "approvals";

const UI_TABS: Array<{ id: UiTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "projects", label: "Projects" },
  { id: "roles", label: "Roles" },
  { id: "skills", label: "Skill Packs" },
  { id: "workflows", label: "Workflows" },
  { id: "runs", label: "Runs" },
  { id: "tasks", label: "Tasks" },
  { id: "approvals", label: "Approvals" }
];

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function createApiError(response: Response): Promise<ApiError> {
  const text = await response.text();
  const message = text.trim().length > 0 ? text : `Request failed with status ${response.status}`;
  return new ApiError(response.status, message);
}

function isApiErrorWithStatus(error: unknown, status: number): boolean {
  return error instanceof ApiError && error.status === status;
}

async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  return (await response.json()) as T;
}

async function apiPut<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  return (await response.json()) as T;
}

async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!response.ok) {
    throw await createApiError(response);
  }
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw await createApiError(response);
  }
  return (await response.json()) as T;
}

function stepsToJson(steps: WorkflowStep[]): string {
  return JSON.stringify(steps, null, 2);
}

const DEFAULT_STEPS_JSON = stepsToJson([
  { step_id: "plan", role_id: 1, title: "Plan", depends_on: [] },
  { step_id: "build", role_id: 1, title: "Build", depends_on: ["plan"] }
]);

export function App() {
  const [activeTab, setActiveTab] = useState<UiTab>("overview");
  const [roleName, setRoleName] = useState("coder");
  const [roleContext7Enabled, setRoleContext7Enabled] = useState(true);
  const [roleSystemPrompt, setRoleSystemPrompt] = useState("");
  const [roleAllowedToolsInput, setRoleAllowedToolsInput] = useState("");
  const [roleSkillPacksInput, setRoleSkillPacksInput] = useState("");
  const [roleConstraintsJson, setRoleConstraintsJson] = useState("{}");
  const [roles, setRoles] = useState<RoleRead[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [skillPackName, setSkillPackName] = useState("core");
  const [skillPackSkillsInput, setSkillPackSkillsInput] = useState("skills/task-governance");
  const [skillPacks, setSkillPacks] = useState<SkillPackRead[]>([]);
  const [selectedSkillPackId, setSelectedSkillPackId] = useState<number | null>(null);

  const [taskTitle, setTaskTitle] = useState("implement context policy");
  const [taskMode, setTaskMode] = useState<Context7Mode>("inherit");
  const [taskExecutionMode, setTaskExecutionMode] = useState<ExecutionMode>("no-workspace");
  const [taskRequiresApproval, setTaskRequiresApproval] = useState(false);
  const [taskProjectIdInput, setTaskProjectIdInput] = useState("");
  const [taskLockPathsInput, setTaskLockPathsInput] = useState("");
  const [task, setTask] = useState<TaskRead | null>(null);
  const [tasks, setTasks] = useState<TaskRead[]>([]);
  const [taskFilterRunIdInput, setTaskFilterRunIdInput] = useState("");

  const [projectName, setProjectName] = useState("workspace-main");
  const [projectRootPath, setProjectRootPath] = useState("/tmp/multyagents/project");
  const [projectAllowedPathsInput, setProjectAllowedPathsInput] = useState("/tmp/multyagents/project/src");
  const [projects, setProjects] = useState<ProjectRead[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const [workflowName, setWorkflowName] = useState("feature-flow");
  const [workflowProjectIdInput, setWorkflowProjectIdInput] = useState("");
  const [workflowStepsJson, setWorkflowStepsJson] = useState(DEFAULT_STEPS_JSON);
  const [workflows, setWorkflows] = useState<WorkflowTemplateRead[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(null);
  const [runWorkflowTemplateIdInput, setRunWorkflowTemplateIdInput] = useState("");
  const [runTaskIdsInput, setRunTaskIdsInput] = useState("");
  const [runInitiatedBy, setRunInitiatedBy] = useState("ui");
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunRead[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<EventRead[]>([]);
  const [runDispatchResult, setRunDispatchResult] = useState<WorkflowRunDispatchReadyResponse | null>(null);

  const [audit, setAudit] = useState<TaskAudit | null>(null);
  const [dispatchResult, setDispatchResult] = useState<DispatchResult | null>(null);
  const [taskApproval, setTaskApproval] = useState<ApprovalRead | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRead[]>([]);
  const [selectedApprovalId, setSelectedApprovalId] = useState<number | null>(null);
  const [approvalLookupIdInput, setApprovalLookupIdInput] = useState("");
  const [approvalActor, setApprovalActor] = useState("operator-ui");
  const [approvalComment, setApprovalComment] = useState("");
  const [taskSearchInput, setTaskSearchInput] = useState("");
  const [runSearchInput, setRunSearchInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selectedRole = useMemo(
    () => roles.find((item) => item.id === selectedRoleId) ?? null,
    [roles, selectedRoleId]
  );
  const selectedRun = useMemo(
    () => workflowRuns.find((item) => item.id === selectedRunId) ?? null,
    [workflowRuns, selectedRunId]
  );
  const roleNameById = useMemo(() => {
    const mapping: Record<number, string> = {};
    roles.forEach((role) => {
      mapping[role.id] = role.name;
    });
    return mapping;
  }, [roles]);
  const filteredTasks = useMemo(() => {
    const query = taskSearchInput.trim().toLowerCase();
    if (query.length === 0) {
      return tasks;
    }
    return tasks.filter((item) => {
      const haystack = [
        String(item.id),
        item.title,
        item.status,
        item.execution_mode,
        String(item.role_id),
        item.project_id === null ? "" : String(item.project_id)
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [taskSearchInput, tasks]);
  const filteredRuns = useMemo(() => {
    const query = runSearchInput.trim().toLowerCase();
    if (query.length === 0) {
      return workflowRuns;
    }
    return workflowRuns.filter((item) => {
      const haystack = [
        String(item.id),
        item.status,
        item.initiated_by ?? "",
        item.workflow_template_id === null ? "" : String(item.workflow_template_id),
        item.task_ids.join(",")
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [runSearchInput, workflowRuns]);
  const selectedApproval = useMemo(
    () => approvals.find((item) => item.id === selectedApprovalId) ?? taskApproval,
    [approvals, selectedApprovalId, taskApproval]
  );
  const pendingApprovalsCount = useMemo(
    () => approvals.filter((item) => item.status === "pending").length,
    [approvals]
  );

  const canCreateTask = selectedRole !== null;
  const canDispatch = task !== null;

  useEffect(() => {
    void loadRoles();
    void loadSkillPacks();
    void loadWorkflows();
    void loadProjects();
    void loadWorkflowRuns();
    void loadTasks();
  }, []);

  useEffect(() => {
    if (tasks.length === 0) {
      setApprovals([]);
      return;
    }
    void refreshApprovals();
  }, [tasks]);

  async function loadRoles() {
    try {
      const items = await apiGet<RoleRead[]>("/roles");
      setRoles(items);
      if (selectedRoleId === null && items.length > 0) {
        selectRole(items[0]);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadSkillPacks() {
    try {
      const items = await apiGet<SkillPackRead[]>("/skill-packs");
      setSkillPacks(items);
      if (selectedSkillPackId === null && items.length > 0) {
        selectSkillPack(items[0]);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadWorkflows() {
    try {
      const items = await apiGet<WorkflowTemplateRead[]>("/workflow-templates");
      setWorkflows(items);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadProjects() {
    try {
      const items = await apiGet<ProjectRead[]>("/projects");
      setProjects(items);
      if (selectedProjectId === null && items.length > 0) {
        selectProject(items[0]);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadWorkflowRuns() {
    try {
      const items = await apiGet<WorkflowRunRead[]>("/workflow-runs");
      setWorkflowRuns(items);
      if (selectedRunId === null && items.length > 0) {
        setSelectedRunId(items[0].id);
        await loadTimelineEvents(items[0].id, null);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadTasks(runId: number | null = null) {
    try {
      const path = runId === null ? "/tasks" : `/tasks?run_id=${runId}`;
      const items = await apiGet<TaskRead[]>(path);
      setTasks(items);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadTimelineEvents(runId: number | null, taskId: number | null) {
    const params = new URLSearchParams();
    params.set("limit", "100");
    if (runId !== null) {
      params.set("run_id", String(runId));
    } else if (taskId !== null) {
      params.set("task_id", String(taskId));
    }

    const query = params.toString();
    const path = query.length > 0 ? `/events?${query}` : "/events";
    const items = await apiGet<EventRead[]>(path);
    setTimelineEvents(items);
  }

  function selectRole(role: RoleRead) {
    setSelectedRoleId(role.id);
    setRoleName(role.name);
    setRoleContext7Enabled(role.context7_enabled);
    setRoleSystemPrompt(role.system_prompt);
    setRoleAllowedToolsInput(role.allowed_tools.join(", "));
    setRoleSkillPacksInput(role.skill_packs.join(", "));
    setRoleConstraintsJson(JSON.stringify(role.execution_constraints, null, 2));
  }

  function selectSkillPack(pack: SkillPackRead) {
    setSelectedSkillPackId(pack.id);
    setSkillPackName(pack.name);
    setSkillPackSkillsInput(pack.skills.join(", "));
  }

  function selectWorkflow(workflow: WorkflowTemplateRead) {
    setSelectedWorkflowId(workflow.id);
    setWorkflowName(workflow.name);
    setWorkflowProjectIdInput(workflow.project_id === null ? "" : String(workflow.project_id));
    setWorkflowStepsJson(stepsToJson(workflow.steps));
  }

  function selectProject(project: ProjectRead) {
    setSelectedProjectId(project.id);
    setProjectName(project.name);
    setProjectRootPath(project.root_path);
    setProjectAllowedPathsInput(project.allowed_paths.join(", "));
  }

  function parseWorkflowPayload() {
    const parsed = JSON.parse(workflowStepsJson) as WorkflowStep[];
    const projectId = workflowProjectIdInput.trim() === "" ? null : Number(workflowProjectIdInput);

    return {
      name: workflowName,
      project_id: Number.isNaN(projectId) ? null : projectId,
      steps: parsed
    };
  }

  function parseLockPaths(input: string): string[] {
    return input
      .split(/\n|,/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  function parseIdList(input: string): number[] {
    return input
      .split(/\n|,/)
      .map((item) => Number(item.trim()))
      .filter((item) => !Number.isNaN(item));
  }

  function parseStringList(input: string): string[] {
    return input
      .split(/\n|,/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  function parseOptionalId(input: string): number | null {
    const value = input.trim();
    if (value.length === 0) {
      return null;
    }
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  }

  function upsertApproval(approval: ApprovalRead) {
    setApprovals((current) => {
      const index = current.findIndex((item) => item.id === approval.id);
      if (index === -1) {
        return [approval, ...current];
      }
      return current.map((item) => (item.id === approval.id ? approval : item));
    });
  }

  async function loadTaskApproval(taskId: number): Promise<ApprovalRead | null> {
    try {
      const approval = await apiGet<ApprovalRead>(`/tasks/${taskId}/approval`);
      setTaskApproval(approval);
      setSelectedApprovalId(approval.id);
      upsertApproval(approval);
      return approval;
    } catch (err) {
      if (isApiErrorWithStatus(err, 404)) {
        setTaskApproval(null);
        return null;
      }
      throw err;
    }
  }

  async function refreshApprovals() {
    setError(null);
    try {
      const candidates = tasks.filter((item) => item.requires_approval);
      if (candidates.length === 0) {
        setApprovals([]);
        return;
      }
      const collected = await Promise.all(
        candidates.map(async (item) => {
          try {
            return await apiGet<ApprovalRead>(`/tasks/${item.id}/approval`);
          } catch (err) {
            if (isApiErrorWithStatus(err, 404)) {
              return null;
            }
            throw err;
          }
        })
      );
      const available = collected.filter((item): item is ApprovalRead => item !== null);
      setApprovals(available);
      if (selectedApprovalId === null && available.length > 0) {
        setSelectedApprovalId(available[0].id);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onLookupApprovalById() {
    const parsed = Number(approvalLookupIdInput.trim());
    if (Number.isNaN(parsed)) {
      setError("Approval ID must be a number.");
      return;
    }
    setError(null);
    try {
      const approval = await apiGet<ApprovalRead>(`/approvals/${parsed}`);
      setSelectedApprovalId(approval.id);
      setTaskApproval((current) => (current?.id === approval.id ? approval : current));
      upsertApproval(approval);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onApprovalDecision(action: "approve" | "reject") {
    if (!selectedApproval) {
      return;
    }
    setError(null);
    try {
      const payload = {
        actor: approvalActor.trim().length > 0 ? approvalActor.trim() : null,
        comment: approvalComment.trim().length > 0 ? approvalComment.trim() : null
      };
      const path =
        action === "approve"
          ? `/approvals/${selectedApproval.id}/approve`
          : `/approvals/${selectedApproval.id}/reject`;
      const updated = await apiPost<ApprovalRead>(path, payload);
      setTaskApproval((current) => (current?.id === updated.id ? updated : current));
      setSelectedApprovalId(updated.id);
      upsertApproval(updated);
      await loadTasks(parseOptionalId(taskFilterRunIdInput));
      await loadTimelineEvents(selectedRunId, updated.task_id);
      if (task?.id === updated.task_id) {
        const currentTask = await apiGet<TaskRead>(`/tasks/${task.id}`);
        setTask(currentTask);
        const currentAudit = await apiGet<TaskAudit>(`/tasks/${task.id}/audit`);
        setAudit(currentAudit);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onRefreshAll() {
    setError(null);
    await Promise.all([loadProjects(), loadRoles(), loadSkillPacks(), loadWorkflows(), loadWorkflowRuns(), loadTasks()]);
  }

  async function onCreateRole(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const executionConstraints = JSON.parse(roleConstraintsJson) as Record<string, unknown>;
      const created = await apiPost<RoleRead>("/roles", {
        name: roleName,
        context7_enabled: roleContext7Enabled,
        system_prompt: roleSystemPrompt,
        allowed_tools: parseStringList(roleAllowedToolsInput),
        skill_packs: parseStringList(roleSkillPacksInput),
        execution_constraints: executionConstraints
      });
      await loadRoles();
      selectRole(created);
      setTask(null);
      setAudit(null);
      setDispatchResult(null);
      setTaskApproval(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCreateProject(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await apiPost<ProjectRead>("/projects", {
        name: projectName,
        root_path: projectRootPath,
        allowed_paths: parseStringList(projectAllowedPathsInput)
      });
      await loadProjects();
      selectProject(created);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onUpdateProject() {
    if (selectedProjectId === null) {
      return;
    }
    setError(null);
    try {
      const updated = await apiPut<ProjectRead>(`/projects/${selectedProjectId}`, {
        name: projectName,
        root_path: projectRootPath,
        allowed_paths: parseStringList(projectAllowedPathsInput)
      });
      await loadProjects();
      selectProject(updated);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDeleteProject() {
    if (selectedProjectId === null) {
      return;
    }
    setError(null);
    try {
      await apiDelete(`/projects/${selectedProjectId}`);
      const remaining = projects.filter((project) => project.id !== selectedProjectId);
      setProjects(remaining);
      if (remaining.length > 0) {
        selectProject(remaining[0]);
      } else {
        setSelectedProjectId(null);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onUpdateRole() {
    if (selectedRoleId === null) {
      return;
    }
    setError(null);
    try {
      const executionConstraints = JSON.parse(roleConstraintsJson) as Record<string, unknown>;
      const updated = await apiPut<RoleRead>(`/roles/${selectedRoleId}`, {
        name: roleName,
        context7_enabled: roleContext7Enabled,
        system_prompt: roleSystemPrompt,
        allowed_tools: parseStringList(roleAllowedToolsInput),
        skill_packs: parseStringList(roleSkillPacksInput),
        execution_constraints: executionConstraints
      });
      await loadRoles();
      selectRole(updated);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCreateSkillPack(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await apiPost<SkillPackRead>("/skill-packs", {
        name: skillPackName,
        skills: parseStringList(skillPackSkillsInput)
      });
      await loadSkillPacks();
      selectSkillPack(created);
      await loadRoles();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onUpdateSkillPack() {
    if (selectedSkillPackId === null) {
      return;
    }
    setError(null);
    try {
      const updated = await apiPut<SkillPackRead>(`/skill-packs/${selectedSkillPackId}`, {
        name: skillPackName,
        skills: parseStringList(skillPackSkillsInput)
      });
      await loadSkillPacks();
      selectSkillPack(updated);
      await loadRoles();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDeleteSkillPack() {
    if (selectedSkillPackId === null) {
      return;
    }
    setError(null);
    try {
      await apiDelete(`/skill-packs/${selectedSkillPackId}`);
      const remaining = skillPacks.filter((item) => item.id !== selectedSkillPackId);
      setSkillPacks(remaining);
      if (remaining.length > 0) {
        selectSkillPack(remaining[0]);
      } else {
        setSelectedSkillPackId(null);
      }
      await loadRoles();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDeleteRole() {
    if (selectedRoleId === null) {
      return;
    }
    setError(null);
    try {
      await apiDelete(`/roles/${selectedRoleId}`);
      const remaining = roles.filter((role) => role.id !== selectedRoleId);
      setRoles(remaining);
      if (remaining.length > 0) {
        selectRole(remaining[0]);
      } else {
        setSelectedRoleId(null);
      }
      setTask(null);
      setAudit(null);
      setDispatchResult(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCreateTask(event: FormEvent) {
    event.preventDefault();
    if (!selectedRole) {
      return;
    }
    setError(null);
    try {
      const parsedProjectId = taskProjectIdInput.trim() === "" ? null : Number(taskProjectIdInput);
      const lockPaths = parseLockPaths(taskLockPathsInput);
      const created = await apiPost<TaskRead>("/tasks", {
        role_id: selectedRole.id,
        title: taskTitle,
        context7_mode: taskMode,
        execution_mode: taskExecutionMode,
        requires_approval: taskRequiresApproval,
        project_id: Number.isNaN(parsedProjectId) ? null : parsedProjectId,
        lock_paths: lockPaths
      });
      setTask(created);
      if (created.requires_approval) {
        await loadTaskApproval(created.id);
      } else {
        setTaskApproval(null);
      }
      await loadTasks(parseOptionalId(taskFilterRunIdInput));
      setAudit(null);
      setDispatchResult(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDispatch() {
    if (!task) {
      return;
    }
    setError(null);
    try {
      const result = await apiPost<DispatchResult>(`/tasks/${task.id}/dispatch`, {});
      setDispatchResult(result);
      const currentTask = await apiGet<TaskRead>(`/tasks/${task.id}`);
      setTask(currentTask);
      if (currentTask.requires_approval) {
        await loadTaskApproval(currentTask.id);
      } else {
        setTaskApproval(null);
      }
      await loadTasks(parseOptionalId(taskFilterRunIdInput));
      const currentAudit = await apiGet<TaskAudit>(`/tasks/${task.id}/audit`);
      setAudit(currentAudit);
      await loadTimelineEvents(selectedRunId, task.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCancelTask() {
    if (!task) {
      return;
    }
    setError(null);
    try {
      const updated = await apiPost<TaskRead>(`/tasks/${task.id}/cancel`, {});
      setTask(updated);
      if (updated.requires_approval) {
        await loadTaskApproval(updated.id);
      } else {
        setTaskApproval(null);
      }
      await loadTasks(parseOptionalId(taskFilterRunIdInput));
      await loadTimelineEvents(selectedRunId, task.id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onRefreshTask() {
    if (!task) {
      return;
    }
    setError(null);
    try {
      const current = await apiGet<TaskRead>(`/tasks/${task.id}`);
      setTask(current);
      if (current.requires_approval) {
        await loadTaskApproval(current.id);
      } else {
        setTaskApproval(null);
      }
      await loadTasks(parseOptionalId(taskFilterRunIdInput));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCreateWorkflowRun(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const parsedTemplateId = runWorkflowTemplateIdInput.trim() === "" ? null : Number(runWorkflowTemplateIdInput);
      const taskIds = parseIdList(runTaskIdsInput);
      const created = await apiPost<WorkflowRunRead>("/workflow-runs", {
        workflow_template_id: Number.isNaN(parsedTemplateId) ? null : parsedTemplateId,
        task_ids: taskIds,
        initiated_by: runInitiatedBy.trim() === "" ? null : runInitiatedBy.trim()
      });
      await loadWorkflowRuns();
      setSelectedRunId(created.id);
      await loadTimelineEvents(created.id, null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onRunAction(action: "pause" | "resume" | "abort") {
    if (selectedRunId === null) {
      return;
    }
    setError(null);
    try {
      await apiPost<WorkflowRunRead>(`/workflow-runs/${selectedRunId}/${action}`, {});
      await loadWorkflowRuns();
      await loadTimelineEvents(selectedRunId, null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDispatchReadyTask() {
    if (selectedRunId === null) {
      return;
    }
    setError(null);
    try {
      const result = await apiPost<WorkflowRunDispatchReadyResponse>(
        `/workflow-runs/${selectedRunId}/dispatch-ready`,
        {}
      );
      setRunDispatchResult(result);
      await loadWorkflowRuns();
      await loadTasks(selectedRunId);
      if (result.task_id !== null) {
        const currentTask = await apiGet<TaskRead>(`/tasks/${result.task_id}`);
        setTask(currentTask);
        const currentAudit = await apiGet<TaskAudit>(`/tasks/${result.task_id}/audit`);
        setAudit(currentAudit);
        setDispatchResult(result.dispatch);
        if (currentTask.requires_approval) {
          await loadTaskApproval(currentTask.id);
        } else {
          setTaskApproval(null);
        }
      }
      await loadTimelineEvents(selectedRunId, result.task_id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onRefreshTimeline() {
    setError(null);
    try {
      await loadTimelineEvents(selectedRunId, task?.id ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onRefreshTasks() {
    setError(null);
    const runId = parseOptionalId(taskFilterRunIdInput);
    await loadTasks(runId);
  }

  async function onCreateWorkflow(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await apiPost<WorkflowTemplateRead>("/workflow-templates", parseWorkflowPayload());
      await loadWorkflows();
      selectWorkflow(created);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onUpdateWorkflow() {
    if (selectedWorkflowId === null) {
      return;
    }
    setError(null);
    try {
      const updated = await apiPut<WorkflowTemplateRead>(
        `/workflow-templates/${selectedWorkflowId}`,
        parseWorkflowPayload()
      );
      await loadWorkflows();
      selectWorkflow(updated);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onDeleteWorkflow() {
    if (selectedWorkflowId === null) {
      return;
    }
    setError(null);
    try {
      await apiDelete(`/workflow-templates/${selectedWorkflowId}`);
      const remaining = workflows.filter((workflow) => workflow.id !== selectedWorkflowId);
      setWorkflows(remaining);
      if (remaining.length > 0) {
        selectWorkflow(remaining[0]);
      } else {
        setSelectedWorkflowId(null);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const cardClass = "rounded-xl border border-slate-200 bg-white p-4 shadow-sm";
  const sectionClass = "rounded-xl border border-slate-200 bg-white p-4 shadow-sm";
  const labelClass = "text-xs font-medium uppercase tracking-wide text-slate-500";
  const inputClass =
    "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-blue-500";
  const textareaClass =
    "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-blue-500";
  const buttonClass =
    "inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40";
  const primaryButtonClass =
    "inline-flex items-center justify-center rounded-lg border border-blue-500 bg-blue-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40";
  const tableClass = "w-full min-w-[720px] border-collapse text-left text-sm";
  const thClass = "border-b border-slate-200 px-2 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500";
  const tdClass = "border-b border-slate-100 px-2 py-2 text-sm text-slate-700";

  return (
    <main className="min-h-screen w-full bg-slate-50 text-slate-900">
      <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Multiagents Control Panel</h1>
            <p className="mt-1 text-sm text-slate-500">API: {API_BASE}</p>
          </div>
          <button type="button" className={primaryButtonClass} onClick={() => void onRefreshAll()}>
            Refresh all
          </button>
        </header>

        <section className="mb-4 grid w-full grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <div className={cardClass}>
            <p className={labelClass}>Projects</p>
            <p className="mt-2 text-2xl font-semibold">{projects.length}</p>
          </div>
          <div className={cardClass}>
            <p className={labelClass}>Roles</p>
            <p className="mt-2 text-2xl font-semibold">{roles.length}</p>
          </div>
          <div className={cardClass}>
            <p className={labelClass}>Skill packs</p>
            <p className="mt-2 text-2xl font-semibold">{skillPacks.length}</p>
          </div>
          <div className={cardClass}>
            <p className={labelClass}>Runs</p>
            <p className="mt-2 text-2xl font-semibold">{workflowRuns.length}</p>
          </div>
          <div className={cardClass}>
            <p className={labelClass}>Tasks</p>
            <p className="mt-2 text-2xl font-semibold">{tasks.length}</p>
          </div>
          <div className={cardClass}>
            <p className={labelClass}>Pending approvals</p>
            <p className="mt-2 text-2xl font-semibold">{pendingApprovalsCount}</p>
          </div>
        </section>

        <nav className="mb-6 flex flex-wrap gap-2">
          {UI_TABS.map((tab) => {
            const active = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={
                  active
                    ? "rounded-lg border border-blue-500 bg-blue-600 px-3 py-2 text-sm font-medium text-white"
                    : "rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-slate-400 hover:bg-slate-50"
                }
              >
                {tab.label}
              </button>
            );
          })}
        </nav>

        {error && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            Error: {error}
          </div>
        )}

        {activeTab === "overview" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Overview</h2>
            <p className="mt-1 text-sm text-slate-500">Use tabs to focus on one domain at a time.</p>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className={labelClass}>Selected run</p>
                <p className="mt-2 text-sm">{selectedRun ? `${selectedRun.id} (${selectedRun.status})` : "none"}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className={labelClass}>Selected task</p>
                <p className="mt-2 text-sm">{task ? `${task.id} (${task.status})` : "none"}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className={labelClass}>Selected approval</p>
                <p className="mt-2 text-sm">{selectedApproval ? `${selectedApproval.id} (${selectedApproval.status})` : "none"}</p>
              </div>
            </div>
          </section>
        )}

        {activeTab === "projects" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Projects</h2>
            <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateProject}>
              <label className="md:col-span-1">
                <span className={labelClass}>Name</span>
                <input className={inputClass} value={projectName} onChange={(e) => setProjectName(e.target.value)} />
              </label>
              <label className="md:col-span-1 xl:col-span-2">
                <span className={labelClass}>Root path</span>
                <input className={inputClass} value={projectRootPath} onChange={(e) => setProjectRootPath(e.target.value)} />
              </label>
              <label className="md:col-span-2 xl:col-span-4">
                <span className={labelClass}>Allowed paths (comma/newline)</span>
                <input className={inputClass} value={projectAllowedPathsInput} onChange={(e) => setProjectAllowedPathsInput(e.target.value)} />
              </label>
              <div className="md:col-span-2 xl:col-span-4 flex flex-wrap gap-2">
                <button type="submit" className={primaryButtonClass}>Create</button>
                <button type="button" className={buttonClass} onClick={onUpdateProject} disabled={selectedProjectId === null}>Update selected</button>
                <button type="button" className={buttonClass} onClick={onDeleteProject} disabled={selectedProjectId === null}>Delete selected</button>
                <button type="button" className={buttonClass} onClick={() => void loadProjects()}>Refresh</button>
              </div>
            </form>

            <div className="mt-4 overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>id</th>
                    <th className={thClass}>name</th>
                    <th className={thClass}>root</th>
                    <th className={thClass}>allowed paths</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => (
                    <tr
                      key={project.id}
                      onClick={() => selectProject(project)}
                      className={`cursor-pointer ${project.id === selectedProjectId ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{project.id}</td>
                      <td className={tdClass}>{project.name}</td>
                      <td className={tdClass}>{project.root_path}</td>
                      <td className={tdClass}>{project.allowed_paths.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "roles" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Roles</h2>
            <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateRole}>
              <label>
                <span className={labelClass}>Role name</span>
                <input className={inputClass} value={roleName} onChange={(e) => setRoleName(e.target.value)} />
              </label>
              <label className="flex items-end gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2">
                <input type="checkbox" checked={roleContext7Enabled} onChange={(e) => setRoleContext7Enabled(e.target.checked)} />
                <span className="text-sm text-slate-700">Context7 default</span>
              </label>
              <label className="xl:col-span-2">
                <span className={labelClass}>Allowed tools (comma/newline)</span>
                <input className={inputClass} value={roleAllowedToolsInput} onChange={(e) => setRoleAllowedToolsInput(e.target.value)} />
              </label>
              <label className="md:col-span-2 xl:col-span-4">
                <span className={labelClass}>System prompt</span>
                <textarea className={textareaClass} rows={3} value={roleSystemPrompt} onChange={(e) => setRoleSystemPrompt(e.target.value)} />
              </label>
              <label className="md:col-span-2 xl:col-span-2">
                <span className={labelClass}>Skill packs (comma/newline)</span>
                <input className={inputClass} value={roleSkillPacksInput} onChange={(e) => setRoleSkillPacksInput(e.target.value)} />
              </label>
              <label className="md:col-span-2 xl:col-span-2">
                <span className={labelClass}>Execution constraints JSON</span>
                <textarea className={textareaClass} rows={3} value={roleConstraintsJson} onChange={(e) => setRoleConstraintsJson(e.target.value)} />
              </label>
              <div className="md:col-span-2 xl:col-span-4 flex flex-wrap gap-2">
                <button type="submit" className={primaryButtonClass}>Create</button>
                <button type="button" className={buttonClass} onClick={onUpdateRole} disabled={selectedRoleId === null}>Update selected</button>
                <button type="button" className={buttonClass} onClick={onDeleteRole} disabled={selectedRoleId === null}>Delete selected</button>
                <button type="button" className={buttonClass} onClick={() => void loadRoles()}>Refresh</button>
              </div>
            </form>

            <div className="mt-2 text-xs text-slate-500">Available skill packs: {skillPacks.map((pack) => pack.name).join(", ") || "none"}</div>

            <div className="mt-4 overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>id</th>
                    <th className={thClass}>name</th>
                    <th className={thClass}>context7</th>
                    <th className={thClass}>tools</th>
                    <th className={thClass}>skill packs</th>
                  </tr>
                </thead>
                <tbody>
                  {roles.map((role) => (
                    <tr
                      key={role.id}
                      onClick={() => selectRole(role)}
                      className={`cursor-pointer ${role.id === selectedRoleId ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{role.id}</td>
                      <td className={tdClass}>{role.name}</td>
                      <td className={tdClass}>{role.context7_enabled ? "on" : "off"}</td>
                      <td className={tdClass}>{role.allowed_tools.join(", ") || "-"}</td>
                      <td className={tdClass}>{role.skill_packs.join(", ") || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "skills" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Skill Packs</h2>
            <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateSkillPack}>
              <label>
                <span className={labelClass}>Name</span>
                <input className={inputClass} value={skillPackName} onChange={(e) => setSkillPackName(e.target.value)} />
              </label>
              <label className="md:col-span-2 xl:col-span-3">
                <span className={labelClass}>Skills (comma/newline)</span>
                <input className={inputClass} value={skillPackSkillsInput} onChange={(e) => setSkillPackSkillsInput(e.target.value)} />
              </label>
              <div className="md:col-span-2 xl:col-span-4 flex flex-wrap gap-2">
                <button type="submit" className={primaryButtonClass}>Create</button>
                <button type="button" className={buttonClass} onClick={onUpdateSkillPack} disabled={selectedSkillPackId === null}>Update selected</button>
                <button type="button" className={buttonClass} onClick={onDeleteSkillPack} disabled={selectedSkillPackId === null}>Delete selected</button>
                <button type="button" className={buttonClass} onClick={() => void loadSkillPacks()}>Refresh</button>
              </div>
            </form>

            <div className="mt-4 overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>id</th>
                    <th className={thClass}>name</th>
                    <th className={thClass}>skills</th>
                    <th className={thClass}>used by roles</th>
                  </tr>
                </thead>
                <tbody>
                  {skillPacks.map((pack) => (
                    <tr
                      key={pack.id}
                      onClick={() => selectSkillPack(pack)}
                      className={`cursor-pointer ${pack.id === selectedSkillPackId ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{pack.id}</td>
                      <td className={tdClass}>{pack.name}</td>
                      <td className={tdClass}>{pack.skills.join(", ") || "-"}</td>
                      <td className={tdClass}>{pack.used_by_role_ids.map((roleId) => roleNameById[roleId] ?? String(roleId)).join(", ") || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "workflows" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Workflow Templates</h2>
            <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateWorkflow}>
              <label>
                <span className={labelClass}>Name</span>
                <input className={inputClass} value={workflowName} onChange={(e) => setWorkflowName(e.target.value)} />
              </label>
              <label>
                <span className={labelClass}>Project ID</span>
                <input className={inputClass} value={workflowProjectIdInput} onChange={(e) => setWorkflowProjectIdInput(e.target.value)} placeholder="optional" />
              </label>
              <div className="md:col-span-2 xl:col-span-2 flex flex-wrap items-end gap-2">
                <button type="submit" className={primaryButtonClass}>Create</button>
                <button type="button" className={buttonClass} onClick={onUpdateWorkflow} disabled={selectedWorkflowId === null}>Update selected</button>
                <button type="button" className={buttonClass} onClick={onDeleteWorkflow} disabled={selectedWorkflowId === null}>Delete selected</button>
                <button type="button" className={buttonClass} onClick={() => void loadWorkflows()}>Refresh</button>
              </div>
              <label className="md:col-span-2 xl:col-span-4">
                <span className={labelClass}>Steps JSON</span>
                <textarea className={textareaClass} rows={10} value={workflowStepsJson} onChange={(e) => setWorkflowStepsJson(e.target.value)} />
              </label>
            </form>

            <div className="mt-4 overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>id</th>
                    <th className={thClass}>name</th>
                    <th className={thClass}>project</th>
                    <th className={thClass}>steps</th>
                  </tr>
                </thead>
                <tbody>
                  {workflows.map((workflow) => (
                    <tr
                      key={workflow.id}
                      onClick={() => selectWorkflow(workflow)}
                      className={`cursor-pointer ${workflow.id === selectedWorkflowId ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{workflow.id}</td>
                      <td className={tdClass}>{workflow.name}</td>
                      <td className={tdClass}>{workflow.project_id ?? "-"}</td>
                      <td className={tdClass}>{workflow.steps.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === "runs" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Workflow Runs and Timeline</h2>
            <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateWorkflowRun}>
              <label>
                <span className={labelClass}>Workflow template ID</span>
                <input className={inputClass} value={runWorkflowTemplateIdInput} onChange={(e) => setRunWorkflowTemplateIdInput(e.target.value)} placeholder="optional" />
              </label>
              <label>
                <span className={labelClass}>Task IDs (comma/newline)</span>
                <input className={inputClass} value={runTaskIdsInput} onChange={(e) => setRunTaskIdsInput(e.target.value)} placeholder="1,2" />
              </label>
              <label>
                <span className={labelClass}>Initiated by</span>
                <input className={inputClass} value={runInitiatedBy} onChange={(e) => setRunInitiatedBy(e.target.value)} />
              </label>
              <label>
                <span className={labelClass}>Search runs</span>
                <input className={inputClass} value={runSearchInput} onChange={(e) => setRunSearchInput(e.target.value)} placeholder="id/status/template" />
              </label>
              <div className="md:col-span-2 xl:col-span-4 flex flex-wrap gap-2">
                <button type="submit" className={primaryButtonClass}>Create run</button>
                <button type="button" className={buttonClass} onClick={() => void loadWorkflowRuns()}>Refresh runs</button>
                <button type="button" className={buttonClass} onClick={() => void onRefreshTimeline()}>Refresh timeline</button>
                <button type="button" className={buttonClass} onClick={() => void onRunAction("pause")} disabled={selectedRunId === null}>Pause run</button>
                <button type="button" className={buttonClass} onClick={() => void onRunAction("resume")} disabled={selectedRunId === null}>Resume run</button>
                <button type="button" className={buttonClass} onClick={() => void onRunAction("abort")} disabled={selectedRunId === null}>Abort run</button>
                <button type="button" className={buttonClass} onClick={onDispatchReadyTask} disabled={selectedRunId === null}>Dispatch ready task</button>
              </div>
            </form>

            <div className="mt-4 overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>id</th>
                    <th className={thClass}>status</th>
                    <th className={thClass}>template</th>
                    <th className={thClass}>tasks</th>
                    <th className={thClass}>updated</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRuns.map((run) => (
                    <tr
                      key={run.id}
                      onClick={() => {
                        setSelectedRunId(run.id);
                        setTaskFilterRunIdInput(String(run.id));
                        void loadTasks(run.id);
                        void loadTimelineEvents(run.id, null);
                      }}
                      className={`cursor-pointer ${run.id === selectedRunId ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{run.id}</td>
                      <td className={tdClass}>{run.status}</td>
                      <td className={tdClass}>{run.workflow_template_id ?? "-"}</td>
                      <td className={tdClass}>{run.task_ids.join(", ") || "-"}</td>
                      <td className={tdClass}>{run.updated_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <div>
                <p className="text-sm text-slate-600">Selected run: {selectedRun ? `${selectedRun.id} (${selectedRun.status})` : "none"}</p>
                {runDispatchResult && (
                  <pre className="mt-2 max-h-72 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                    {JSON.stringify(runDispatchResult, null, 2)}
                  </pre>
                )}
              </div>
              <pre className="max-h-72 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                {JSON.stringify(timelineEvents, null, 2)}
              </pre>
            </div>
          </section>
        )}

        {activeTab === "tasks" && (
          <div className="space-y-4">
            <section className={sectionClass}>
              <h2 className="text-lg font-semibold">Task Explorer</h2>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-5">
                <label>
                  <span className={labelClass}>Run ID filter</span>
                  <input className={inputClass} value={taskFilterRunIdInput} onChange={(e) => setTaskFilterRunIdInput(e.target.value)} placeholder="optional" />
                </label>
                <label className="md:col-span-2 xl:col-span-2">
                  <span className={labelClass}>Search tasks</span>
                  <input className={inputClass} value={taskSearchInput} onChange={(e) => setTaskSearchInput(e.target.value)} placeholder="id/title/status" />
                </label>
                <div className="md:col-span-3 xl:col-span-2 flex flex-wrap items-end gap-2">
                  <button type="button" className={buttonClass} onClick={() => void onRefreshTasks()}>Refresh tasks</button>
                  <button
                    type="button"
                    className={buttonClass}
                    onClick={() => {
                      setTaskFilterRunIdInput("");
                      setTaskSearchInput("");
                      void loadTasks();
                    }}
                  >
                    Clear filter
                  </button>
                </div>
              </div>

              <div className="mt-4 overflow-x-auto">
                <table className={tableClass}>
                  <thead>
                    <tr>
                      <th className={thClass}>id</th>
                      <th className={thClass}>title</th>
                      <th className={thClass}>status</th>
                      <th className={thClass}>mode</th>
                      <th className={thClass}>role</th>
                      <th className={thClass}>project</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTasks.map((item) => (
                      <tr
                        key={item.id}
                        onClick={() => {
                          setTask(item);
                          if (item.requires_approval) {
                            void loadTaskApproval(item.id);
                          } else {
                            setTaskApproval(null);
                          }
                          void loadTimelineEvents(selectedRunId, item.id);
                        }}
                        className={`cursor-pointer ${task?.id === item.id ? "bg-blue-50" : "hover:bg-slate-50"}`}
                      >
                        <td className={tdClass}>{item.id}</td>
                        <td className={tdClass}>{item.title}</td>
                        <td className={tdClass}>{item.status}</td>
                        <td className={tdClass}>{item.execution_mode}</td>
                        <td className={tdClass}>{item.role_id}</td>
                        <td className={tdClass}>{item.project_id ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className={sectionClass}>
              <h2 className="text-lg font-semibold">Create Task</h2>
              <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateTask}>
                <label>
                  <span className={labelClass}>Role</span>
                  <select
                    className={inputClass}
                    value={selectedRoleId ?? ""}
                    onChange={(e) => {
                      if (e.target.value === "") {
                        setSelectedRoleId(null);
                        return;
                      }
                      const parsed = Number(e.target.value);
                      const nextRole = roles.find((role) => role.id === parsed);
                      if (nextRole) {
                        selectRole(nextRole);
                      }
                    }}
                  >
                    <option value="">select role</option>
                    {roles.map((role) => (
                      <option key={role.id} value={String(role.id)}>
                        {role.id}: {role.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className={labelClass}>Title</span>
                  <input className={inputClass} value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} disabled={!canCreateTask} />
                </label>
                <label>
                  <span className={labelClass}>Context7 mode</span>
                  <select className={inputClass} value={taskMode} onChange={(e) => setTaskMode(e.target.value as Context7Mode)} disabled={!canCreateTask}>
                    <option value="inherit">inherit</option>
                    <option value="force_on">force_on</option>
                    <option value="force_off">force_off</option>
                  </select>
                </label>
                <label>
                  <span className={labelClass}>Execution mode</span>
                  <select
                    className={inputClass}
                    value={taskExecutionMode}
                    onChange={(e) => setTaskExecutionMode(e.target.value as ExecutionMode)}
                    disabled={!canCreateTask}
                  >
                    <option value="no-workspace">no-workspace</option>
                    <option value="shared-workspace">shared-workspace</option>
                    <option value="isolated-worktree">isolated-worktree</option>
                    <option value="docker-sandbox">docker-sandbox</option>
                  </select>
                </label>
                <label>
                  <span className={labelClass}>Project ID</span>
                  <input className={inputClass} value={taskProjectIdInput} onChange={(e) => setTaskProjectIdInput(e.target.value)} disabled={!canCreateTask} placeholder="optional" />
                </label>
                <label className="flex items-end gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2">
                  <input
                    type="checkbox"
                    checked={taskRequiresApproval}
                    onChange={(e) => setTaskRequiresApproval(e.target.checked)}
                    disabled={!canCreateTask}
                  />
                  <span className="text-sm text-slate-700">Requires approval</span>
                </label>
                <label className="md:col-span-2 xl:col-span-4">
                  <span className={labelClass}>Lock paths (comma/newline)</span>
                  <textarea
                    className={textareaClass}
                    value={taskLockPathsInput}
                    onChange={(e) => setTaskLockPathsInput(e.target.value)}
                    rows={3}
                    placeholder="/abs/path/one&#10;/abs/path/two"
                    disabled={!canCreateTask}
                  />
                </label>
                <div className="md:col-span-2 xl:col-span-4 flex flex-wrap gap-2">
                  <button type="submit" className={primaryButtonClass} disabled={!canCreateTask}>Save task</button>
                  <button type="button" className={buttonClass} onClick={() => void loadProjects()}>Refresh projects</button>
                </div>
              </form>
              {projects.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">Known projects: {projects.map((project) => `${project.id}:${project.name}`).join(", ")}</p>
              )}
              {task && <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">{JSON.stringify(task, null, 2)}</pre>}
            </section>

            <section className={sectionClass}>
              <h2 className="text-lg font-semibold">Dispatch and Audit</h2>
              <div className="mt-4 flex flex-wrap gap-2">
                <button className={primaryButtonClass} onClick={onDispatch} disabled={!canDispatch}>Dispatch task</button>
                <button className={buttonClass} onClick={onCancelTask} disabled={!task}>Cancel task</button>
                <button className={buttonClass} onClick={onRefreshTask} disabled={!task}>Refresh task</button>
                <button
                  type="button"
                  className={buttonClass}
                  disabled={!task?.requires_approval}
                  onClick={() => {
                    if (task) {
                      void loadTaskApproval(task.id);
                    }
                    setActiveTab("approvals");
                  }}
                >
                  Open approval
                </button>
              </div>
              {dispatchResult && <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">{JSON.stringify(dispatchResult, null, 2)}</pre>}
              {audit && <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">{JSON.stringify(audit, null, 2)}</pre>}
              {taskApproval && <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">{JSON.stringify(taskApproval, null, 2)}</pre>}
            </section>
          </div>
        )}

        {activeTab === "approvals" && (
          <section className={sectionClass}>
            <h2 className="text-lg font-semibold">Approvals Inbox</h2>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="flex flex-wrap items-end gap-2">
                <button type="button" className={buttonClass} onClick={() => void refreshApprovals()}>
                  Refresh approvals
                </button>
              </div>
              <label>
                <span className={labelClass}>Approval ID</span>
                <input className={inputClass} value={approvalLookupIdInput} onChange={(e) => setApprovalLookupIdInput(e.target.value)} />
              </label>
              <div className="flex items-end">
                <button type="button" className={buttonClass} onClick={() => void onLookupApprovalById()}>
                  Load by ID
                </button>
              </div>
              <div />
              <label>
                <span className={labelClass}>Actor</span>
                <input className={inputClass} value={approvalActor} onChange={(e) => setApprovalActor(e.target.value)} />
              </label>
              <label className="md:col-span-2">
                <span className={labelClass}>Comment</span>
                <input className={inputClass} value={approvalComment} onChange={(e) => setApprovalComment(e.target.value)} />
              </label>
              <div className="flex flex-wrap items-end gap-2">
                <button
                  type="button"
                  className={primaryButtonClass}
                  onClick={() => void onApprovalDecision("approve")}
                  disabled={selectedApproval?.status !== "pending"}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className={buttonClass}
                  onClick={() => void onApprovalDecision("reject")}
                  disabled={selectedApproval?.status !== "pending"}
                >
                  Reject
                </button>
              </div>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className={tableClass}>
                <thead>
                  <tr>
                    <th className={thClass}>id</th>
                    <th className={thClass}>task</th>
                    <th className={thClass}>status</th>
                    <th className={thClass}>decided by</th>
                    <th className={thClass}>comment</th>
                  </tr>
                </thead>
                <tbody>
                  {approvals.map((approval) => (
                    <tr
                      key={approval.id}
                      onClick={() => {
                        setSelectedApprovalId(approval.id);
                        setTaskApproval(approval);
                      }}
                      className={`cursor-pointer ${selectedApproval?.id === approval.id ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{approval.id}</td>
                      <td className={tdClass}>{approval.task_id}</td>
                      <td className={tdClass}>{approval.status}</td>
                      <td className={tdClass}>{approval.decided_by ?? "-"}</td>
                      <td className={tdClass}>{approval.comment ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
