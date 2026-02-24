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

  return (
    <main style={{ maxWidth: 1180, margin: "0 auto", padding: 24, fontFamily: "Inter, system-ui, sans-serif", color: "#24292f" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>Control Panel</h1>
          <p style={{ margin: 0, color: "#57606a" }}>API: {API_BASE}</p>
        </div>
        <button type="button" onClick={() => void onRefreshAll()}>
          Refresh all
        </button>
      </div>

      <div
        style={{
          marginTop: 12,
          marginBottom: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: 8
        }}
      >
        <div style={{ border: "1px solid #d0d7de", borderRadius: 8, padding: 10 }}>
          <strong>Projects</strong>
          <div>{projects.length}</div>
        </div>
        <div style={{ border: "1px solid #d0d7de", borderRadius: 8, padding: 10 }}>
          <strong>Roles</strong>
          <div>{roles.length}</div>
        </div>
        <div style={{ border: "1px solid #d0d7de", borderRadius: 8, padding: 10 }}>
          <strong>Runs</strong>
          <div>{workflowRuns.length}</div>
        </div>
        <div style={{ border: "1px solid #d0d7de", borderRadius: 8, padding: 10 }}>
          <strong>Tasks</strong>
          <div>{tasks.length}</div>
        </div>
        <div style={{ border: "1px solid #d0d7de", borderRadius: 8, padding: 10 }}>
          <strong>Pending approvals</strong>
          <div>{pendingApprovalsCount}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {UI_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            style={{
              borderRadius: 8,
              border: "1px solid #d0d7de",
              padding: "6px 10px",
              cursor: "pointer",
              backgroundColor: activeTab === tab.id ? "#0969da" : "#ffffff",
              color: activeTab === tab.id ? "#ffffff" : "#24292f"
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "overview" ? "block" : "none" }}>
        <h2>Overview</h2>
        <p style={{ marginTop: 0 }}>Select a tab to focus on one workflow area.</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 8 }}>
          <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
            <strong>Selected run</strong>
            <div>{selectedRun ? `${selectedRun.id} (${selectedRun.status})` : "none"}</div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
            <strong>Selected task</strong>
            <div>{task ? `${task.id} (${task.status})` : "none"}</div>
          </div>
          <div style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
            <strong>Selected approval</strong>
            <div>{selectedApproval ? `${selectedApproval.id} (${selectedApproval.status})` : "none"}</div>
          </div>
        </div>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "projects" ? "block" : "none" }}>
        <h2>Projects</h2>
        <form onSubmit={onCreateProject} style={{ marginBottom: 12 }}>
          <label>
            Name
            <input value={projectName} onChange={(e) => setProjectName(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
          <label style={{ marginLeft: 16 }}>
            Root path
            <input value={projectRootPath} onChange={(e) => setProjectRootPath(e.target.value)} style={{ marginLeft: 8, width: 320 }} />
          </label>
          <button type="submit" style={{ marginLeft: 16 }}>
            Create project
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onUpdateProject} disabled={selectedProjectId === null}>
            Update selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onDeleteProject} disabled={selectedProjectId === null}>
            Delete selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void loadProjects()}>
            Refresh
          </button>
          <div style={{ marginTop: 8 }}>
            <label>
              Allowed paths (comma/newline)
              <input
                value={projectAllowedPathsInput}
                onChange={(e) => setProjectAllowedPathsInput(e.target.value)}
                style={{ marginLeft: 8, width: 500 }}
              />
            </label>
          </div>
        </form>

        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>name</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>root</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>allowed paths</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr
                key={project.id}
                onClick={() => selectProject(project)}
                style={{ cursor: "pointer", backgroundColor: project.id === selectedProjectId ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{project.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{project.name}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{project.root_path}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{project.allowed_paths.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "roles" ? "block" : "none" }}>
        <h2>Roles</h2>
        <form onSubmit={onCreateRole} style={{ marginBottom: 12 }}>
          <label>
            Role name
            <input value={roleName} onChange={(e) => setRoleName(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
          <label style={{ marginLeft: 16 }}>
            Context7 default
            <input
              type="checkbox"
              checked={roleContext7Enabled}
              onChange={(e) => setRoleContext7Enabled(e.target.checked)}
              style={{ marginLeft: 8 }}
            />
          </label>
          <button type="submit" style={{ marginLeft: 16 }}>
            Create role
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onUpdateRole} disabled={selectedRoleId === null}>
            Update selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onDeleteRole} disabled={selectedRoleId === null}>
            Delete selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void loadRoles()}>
            Refresh
          </button>
          <div style={{ marginTop: 12 }}>
            <label style={{ display: "block" }}>
              System prompt
              <textarea
                value={roleSystemPrompt}
                onChange={(e) => setRoleSystemPrompt(e.target.value)}
                rows={3}
                style={{ display: "block", width: "100%", marginTop: 6, fontFamily: "inherit" }}
              />
            </label>
          </div>
          <div style={{ marginTop: 8 }}>
            <label>
              Allowed tools (comma/newline)
              <input
                value={roleAllowedToolsInput}
                onChange={(e) => setRoleAllowedToolsInput(e.target.value)}
                style={{ marginLeft: 8, width: 300 }}
                placeholder="read, write, terminal"
              />
            </label>
          </div>
          <div style={{ marginTop: 8 }}>
            <label>
              Skill packs (comma/newline)
              <input
                value={roleSkillPacksInput}
                onChange={(e) => setRoleSkillPacksInput(e.target.value)}
                style={{ marginLeft: 8, width: 300 }}
                placeholder="core, planning"
              />
            </label>
            {skillPacks.length > 0 && (
              <div style={{ marginTop: 6 }}>
                <strong>Available:</strong> {skillPacks.map((pack) => pack.name).join(", ")}
              </div>
            )}
          </div>
          <div style={{ marginTop: 8 }}>
            <label style={{ display: "block" }}>
              Execution constraints JSON
              <textarea
                value={roleConstraintsJson}
                onChange={(e) => setRoleConstraintsJson(e.target.value)}
                rows={4}
                style={{ display: "block", width: "100%", marginTop: 6, fontFamily: "inherit" }}
              />
            </label>
          </div>
        </form>

        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>name</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>context7</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>tools</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>skills</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((role) => (
              <tr
                key={role.id}
                onClick={() => selectRole(role)}
                style={{ cursor: "pointer", backgroundColor: role.id === selectedRoleId ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{role.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{role.name}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{role.context7_enabled ? "on" : "off"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{role.allowed_tools.join(", ") || "-"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{role.skill_packs.join(", ") || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "skills" ? "block" : "none" }}>
        <h2>Skill Packs</h2>
        <form onSubmit={onCreateSkillPack} style={{ marginBottom: 12 }}>
          <label>
            Name
            <input value={skillPackName} onChange={(e) => setSkillPackName(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
          <button type="submit" style={{ marginLeft: 16 }}>
            Create skill pack
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onUpdateSkillPack} disabled={selectedSkillPackId === null}>
            Update selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onDeleteSkillPack} disabled={selectedSkillPackId === null}>
            Delete selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void loadSkillPacks()}>
            Refresh
          </button>
          <div style={{ marginTop: 8 }}>
            <label>
              Skills (comma/newline)
              <input
                value={skillPackSkillsInput}
                onChange={(e) => setSkillPackSkillsInput(e.target.value)}
                style={{ marginLeft: 8, width: 540 }}
                placeholder="skills/task-governance, skills/api-orchestrator-fastapi"
              />
            </label>
          </div>
        </form>

        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>name</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>skills</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>used by roles</th>
            </tr>
          </thead>
          <tbody>
            {skillPacks.map((pack) => (
              <tr
                key={pack.id}
                onClick={() => selectSkillPack(pack)}
                style={{ cursor: "pointer", backgroundColor: pack.id === selectedSkillPackId ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{pack.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{pack.name}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{pack.skills.join(", ") || "-"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>
                  {pack.used_by_role_ids.map((roleId) => roleNameById[roleId] ?? String(roleId)).join(", ") || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "workflows" ? "block" : "none" }}>
        <h2>Workflow Templates</h2>
        <form onSubmit={onCreateWorkflow}>
          <label>
            Name
            <input value={workflowName} onChange={(e) => setWorkflowName(e.target.value)} style={{ marginLeft: 8 }} />
          </label>
          <label style={{ marginLeft: 16 }}>
            Project ID
            <input
              value={workflowProjectIdInput}
              onChange={(e) => setWorkflowProjectIdInput(e.target.value)}
              style={{ marginLeft: 8, width: 100 }}
              placeholder="optional"
            />
          </label>
          <button type="submit" style={{ marginLeft: 16 }}>
            Create workflow
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onUpdateWorkflow} disabled={selectedWorkflowId === null}>
            Update selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onDeleteWorkflow} disabled={selectedWorkflowId === null}>
            Delete selected
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void loadWorkflows()}>
            Refresh
          </button>
          <div style={{ marginTop: 12 }}>
            <label>
              Steps JSON
              <textarea
                value={workflowStepsJson}
                onChange={(e) => setWorkflowStepsJson(e.target.value)}
                rows={10}
                style={{ display: "block", width: "100%", marginTop: 6, fontFamily: "inherit" }}
              />
            </label>
          </div>
        </form>

        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>name</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>project</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>steps</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((workflow) => (
              <tr
                key={workflow.id}
                onClick={() => selectWorkflow(workflow)}
                style={{ cursor: "pointer", backgroundColor: workflow.id === selectedWorkflowId ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{workflow.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{workflow.name}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{workflow.project_id ?? "-"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{workflow.steps.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "runs" ? "block" : "none" }}>
        <h2>Workflow Runs and Timeline</h2>
        <form onSubmit={onCreateWorkflowRun}>
          <label>
            Workflow template ID
            <input
              value={runWorkflowTemplateIdInput}
              onChange={(e) => setRunWorkflowTemplateIdInput(e.target.value)}
              style={{ marginLeft: 8, width: 120 }}
              placeholder="optional"
            />
          </label>
          <label style={{ marginLeft: 16 }}>
            Task IDs (comma/newline)
            <input
              value={runTaskIdsInput}
              onChange={(e) => setRunTaskIdsInput(e.target.value)}
              style={{ marginLeft: 8, width: 220 }}
              placeholder="1,2"
            />
          </label>
          <label style={{ marginLeft: 16 }}>
            Initiated by
            <input value={runInitiatedBy} onChange={(e) => setRunInitiatedBy(e.target.value)} style={{ marginLeft: 8, width: 120 }} />
          </label>
          <button type="submit" style={{ marginLeft: 16 }}>
            Create run
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void loadWorkflowRuns()}>
            Refresh runs
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void onRefreshTimeline()}>
            Refresh timeline
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void onRunAction("pause")} disabled={selectedRunId === null}>
            Pause run
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void onRunAction("resume")} disabled={selectedRunId === null}>
            Resume run
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void onRunAction("abort")} disabled={selectedRunId === null}>
            Abort run
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={onDispatchReadyTask} disabled={selectedRunId === null}>
            Dispatch ready task
          </button>
        </form>

        <div style={{ marginTop: 10 }}>
          <label>
            Search runs
            <input
              value={runSearchInput}
              onChange={(e) => setRunSearchInput(e.target.value)}
              style={{ marginLeft: 8, width: 240 }}
              placeholder="id/status/template"
            />
          </label>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>status</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>template</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>tasks</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>updated</th>
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
                style={{ cursor: "pointer", backgroundColor: run.id === selectedRunId ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{run.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{run.status}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{run.workflow_template_id ?? "-"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{run.task_ids.join(", ") || "-"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{run.updated_at}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ marginTop: 12 }}>
          <strong>Selected run:</strong> {selectedRun ? `${selectedRun.id} (${selectedRun.status})` : "none"}
        </div>
        {runDispatchResult && <pre style={{ marginTop: 8 }}>{JSON.stringify(runDispatchResult, null, 2)}</pre>}
        <pre style={{ marginTop: 8 }}>{JSON.stringify(timelineEvents, null, 2)}</pre>
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginBottom: 16, display: activeTab === "tasks" ? "block" : "none" }}>
        <h2>Task Explorer</h2>
        <label>
          Run ID filter
          <input
            value={taskFilterRunIdInput}
            onChange={(e) => setTaskFilterRunIdInput(e.target.value)}
            style={{ marginLeft: 8, width: 120 }}
            placeholder="optional"
          />
        </label>
        <label style={{ marginLeft: 8 }}>
          Search
          <input
            value={taskSearchInput}
            onChange={(e) => setTaskSearchInput(e.target.value)}
            style={{ marginLeft: 8, width: 220 }}
            placeholder="id/title/status"
          />
        </label>
        <button type="button" style={{ marginLeft: 8 }} onClick={() => void onRefreshTasks()}>
          Refresh tasks
        </button>
        <button
          type="button"
          style={{ marginLeft: 8 }}
          onClick={() => {
            setTaskFilterRunIdInput("");
            setTaskSearchInput("");
            void loadTasks();
          }}
        >
          Clear filter
        </button>
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>title</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>status</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>mode</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>role</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>project</th>
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
                style={{ cursor: "pointer", backgroundColor: task?.id === item.id ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{item.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{item.title}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{item.status}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{item.execution_mode}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{item.role_id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{item.project_id ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section
        style={{
          border: "1px solid #ddd",
          padding: 16,
          marginBottom: 16,
          opacity: canCreateTask ? 1 : 0.6,
          display: activeTab === "tasks" ? "block" : "none"
        }}
      >
        <h2>Create Task</h2>
        <form onSubmit={onCreateTask}>
          <label>
            Role
            <select
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
              style={{ marginLeft: 8, minWidth: 220 }}
            >
              <option value="">select role</option>
              {roles.map((role) => (
                <option key={role.id} value={String(role.id)}>
                  {role.id}: {role.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ marginLeft: 16 }}>
            Title
            <input value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} style={{ marginLeft: 8 }} disabled={!canCreateTask} />
          </label>
          <label style={{ marginLeft: 16 }}>
            Context7 mode
            <select value={taskMode} onChange={(e) => setTaskMode(e.target.value as Context7Mode)} style={{ marginLeft: 8 }} disabled={!canCreateTask}>
              <option value="inherit">inherit</option>
              <option value="force_on">force_on</option>
              <option value="force_off">force_off</option>
            </select>
          </label>
          <label style={{ marginLeft: 16 }}>
            Execution mode
            <select
              value={taskExecutionMode}
              onChange={(e) => setTaskExecutionMode(e.target.value as ExecutionMode)}
              style={{ marginLeft: 8 }}
              disabled={!canCreateTask}
            >
              <option value="no-workspace">no-workspace</option>
              <option value="shared-workspace">shared-workspace</option>
              <option value="isolated-worktree">isolated-worktree</option>
              <option value="docker-sandbox">docker-sandbox</option>
            </select>
          </label>
          <label style={{ marginLeft: 16 }}>
            Requires approval
            <input
              type="checkbox"
              checked={taskRequiresApproval}
              onChange={(e) => setTaskRequiresApproval(e.target.checked)}
              style={{ marginLeft: 8 }}
              disabled={!canCreateTask}
            />
          </label>
          <label style={{ marginLeft: 16 }}>
            Project ID
            <input
              value={taskProjectIdInput}
              onChange={(e) => setTaskProjectIdInput(e.target.value)}
              style={{ marginLeft: 8, width: 100 }}
              disabled={!canCreateTask}
              placeholder="shared mode"
            />
          </label>
          <button type="submit" style={{ marginLeft: 16 }} disabled={!canCreateTask}>
            Save task
          </button>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void loadProjects()}>
            Refresh projects
          </button>
          <div style={{ marginTop: 12 }}>
            <label>
              Lock paths (newline or comma separated)
              <textarea
                value={taskLockPathsInput}
                onChange={(e) => setTaskLockPathsInput(e.target.value)}
                rows={3}
                style={{ display: "block", width: "100%", marginTop: 6, fontFamily: "inherit" }}
                placeholder="/abs/path/one&#10;/abs/path/two"
                disabled={!canCreateTask}
              />
            </label>
          </div>
        </form>
        {projects.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <strong>Known projects:</strong>{" "}
            {projects.map((project) => `${project.id}:${project.name}`).join(", ")}
          </div>
        )}
        {task && <pre>{JSON.stringify(task, null, 2)}</pre>}
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, display: activeTab === "tasks" ? "block" : "none" }}>
        <h2>Dispatch and Audit</h2>
        <button onClick={onDispatch} disabled={!canDispatch}>
          Dispatch task
        </button>
        <button onClick={onCancelTask} style={{ marginLeft: 8 }} disabled={!task}>
          Cancel task
        </button>
        <button onClick={onRefreshTask} style={{ marginLeft: 8 }} disabled={!task}>
          Refresh task
        </button>
        <button
          type="button"
          style={{ marginLeft: 8 }}
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
        {dispatchResult && <pre>{JSON.stringify(dispatchResult, null, 2)}</pre>}
        {audit && <pre>{JSON.stringify(audit, null, 2)}</pre>}
        {taskApproval && <pre>{JSON.stringify(taskApproval, null, 2)}</pre>}
      </section>

      <section style={{ border: "1px solid #ddd", padding: 16, marginTop: 16, display: activeTab === "approvals" ? "block" : "none" }}>
        <h2>Approvals Inbox</h2>
        <div>
          <button type="button" onClick={() => void refreshApprovals()}>
            Refresh approvals
          </button>
          <label style={{ marginLeft: 8 }}>
            Approval ID
            <input
              value={approvalLookupIdInput}
              onChange={(e) => setApprovalLookupIdInput(e.target.value)}
              style={{ marginLeft: 8, width: 100 }}
            />
          </label>
          <button type="button" style={{ marginLeft: 8 }} onClick={() => void onLookupApprovalById()}>
            Load by id
          </button>
        </div>

        <div style={{ marginTop: 10 }}>
          <label>
            Actor
            <input
              value={approvalActor}
              onChange={(e) => setApprovalActor(e.target.value)}
              style={{ marginLeft: 8, width: 180 }}
            />
          </label>
          <label style={{ marginLeft: 12 }}>
            Comment
            <input
              value={approvalComment}
              onChange={(e) => setApprovalComment(e.target.value)}
              style={{ marginLeft: 8, width: 300 }}
            />
          </label>
          <button
            type="button"
            style={{ marginLeft: 8 }}
            onClick={() => void onApprovalDecision("approve")}
            disabled={selectedApproval?.status !== "pending"}
          >
            Approve
          </button>
          <button
            type="button"
            style={{ marginLeft: 8 }}
            onClick={() => void onApprovalDecision("reject")}
            disabled={selectedApproval?.status !== "pending"}
          >
            Reject
          </button>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>id</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>task</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>status</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>decided by</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>comment</th>
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
                style={{ cursor: "pointer", backgroundColor: selectedApproval?.id === approval.id ? "#f2f2f2" : "transparent" }}
              >
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{approval.id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{approval.task_id}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{approval.status}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{approval.decided_by ?? "-"}</td>
                <td style={{ borderBottom: "1px solid #eee", padding: "4px 0" }}>{approval.comment ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {error && (
        <p style={{ color: "#a00000", marginTop: 16 }}>
          Error: {error}
        </p>
      )}
    </main>
  );
}
