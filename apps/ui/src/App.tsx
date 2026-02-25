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
import { AdminSidebar } from "./components/AdminSidebar";
import { AdminTopBar } from "./components/AdminTopBar";
import { ApprovalsSection } from "./components/ApprovalsSection";
import { OverviewSection } from "./components/OverviewSection";
import { RunsCenterSection } from "./components/RunsCenterSection";
import {
  createWorkflowStepDraft,
  parseWorkflowStepsJson,
  validateWorkflowStepDrafts,
  workflowDraftsToSteps,
  workflowStepsToDrafts
} from "./components/workflowEditorUtils";
import type { WorkflowStepDraft, WorkflowStepDraftFieldErrors } from "./components/workflowEditorUtils";
import type {
  ApprovalRead,
  DispatchResult,
  ProjectRead,
  SkillPackRead,
  UiTab,
  WorkflowRunDispatchReadyResponse,
  WorkflowRunPartialRerunRequest,
  WorkflowRunPartialRerunResponse,
  WorkflowStep,
  WorkflowTemplateRead
} from "./types/controlPanel";
import { UI_TABS } from "./types/controlPanel";

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

type WorkflowEditorMode = "quick" | "json";
type WorkflowPresetId =
  | "feature-delivery"
  | "bugfix-fast-lane"
  | "docs-research-lane"
  | "article-pipeline"
  | "social-pipeline"
  | "localization-pipeline";

type WorkflowPreset = {
  id: WorkflowPresetId;
  label: string;
  scenario: string;
  defaultWorkflowName: string;
  steps: Array<{
    step_id: string;
    title: string;
    depends_on: string[];
  }>;
};

function stepsToJson(steps: unknown[]): string {
  return JSON.stringify(steps, null, 2);
}

function describeWorkflowDraft(draft: WorkflowStepDraft, index: number): string {
  const stepId = draft.step_id.trim();
  if (stepId.length === 0) {
    return `Step ${index + 1}`;
  }
  return `Step ${index + 1} (${stepId})`;
}

function collectStepErrorMessages(stepErrors: Record<string, string | undefined>): string[] {
  return Object.values(stepErrors).filter((message): message is string => typeof message === "string" && message.length > 0);
}

function collectWorkflowValidationSummary(
  drafts: WorkflowStepDraft[],
  formErrors: string[],
  stepErrorsByClientId: Record<string, WorkflowStepDraftFieldErrors>
): string[] {
  const messages = [...formErrors];
  const fieldLabels: Record<string, string> = {
    step_id: "step_id",
    role_id: "role",
    prompt: "prompt",
    depends_on: "depends_on"
  };

  drafts.forEach((draft, index) => {
    const stepErrors = stepErrorsByClientId[draft.client_id];
    if (!stepErrors) {
      return;
    }
    Object.entries(stepErrors).forEach(([field, message]) => {
      if (!message) {
        return;
      }
      messages.push(`${describeWorkflowDraft(draft, index)} [${fieldLabels[field] ?? field}]: ${message}`);
    });
  });

  return messages;
}

const DEFAULT_WORKFLOW_STEPS: WorkflowStep[] = [
  { step_id: "plan", role_id: 1, title: "Plan", depends_on: [] },
  { step_id: "build", role_id: 1, title: "Build", depends_on: ["plan"] }
];
const DEFAULT_STEPS_JSON = stepsToJson(DEFAULT_WORKFLOW_STEPS);
const DEFAULT_WORKFLOW_PRESET_ID: WorkflowPresetId = "feature-delivery";
const WORKFLOW_PRESETS: WorkflowPreset[] = [
  {
    id: "feature-delivery",
    label: "Feature delivery",
    scenario: "Plan, implement, test, and review a product increment with explicit quality gates.",
    defaultWorkflowName: "feature-delivery",
    steps: [
      { step_id: "plan", title: "Clarify scope and break work into concrete implementation steps.", depends_on: [] },
      {
        step_id: "implement",
        title: "Implement the feature changes and keep notes for reviewers.",
        depends_on: ["plan"]
      },
      {
        step_id: "test",
        title: "Run relevant tests and verify acceptance criteria with evidence.",
        depends_on: ["implement"]
      },
      {
        step_id: "review",
        title: "Review final diff, risks, and rollout notes before completion.",
        depends_on: ["test"]
      }
    ]
  },
  {
    id: "bugfix-fast-lane",
    label: "Bugfix fast lane",
    scenario: "Triage, patch, and verify urgent defects with a short delivery path.",
    defaultWorkflowName: "bugfix-fast-lane",
    steps: [
      { step_id: "triage", title: "Reproduce the bug and isolate root cause quickly.", depends_on: [] },
      {
        step_id: "fix",
        title: "Implement the smallest safe patch and document behavioral impact.",
        depends_on: ["triage"]
      },
      {
        step_id: "verify",
        title: "Run focused regression checks and confirm the bug is resolved.",
        depends_on: ["fix"]
      }
    ]
  },
  {
    id: "docs-research-lane",
    label: "Docs / research lane",
    scenario: "Gather facts, synthesize findings, and publish operator-ready documentation.",
    defaultWorkflowName: "docs-research-lane",
    steps: [
      { step_id: "research", title: "Collect relevant sources, constraints, and open questions.", depends_on: [] },
      {
        step_id: "synthesize",
        title: "Synthesize findings into recommendations and key decisions.",
        depends_on: ["research"]
      },
      {
        step_id: "publish",
        title: "Draft final documentation with references and action items.",
        depends_on: ["synthesize"]
      }
    ]
  },
  {
    id: "article-pipeline",
    label: "Article pipeline",
    scenario: "Produce a long-form article from research through editorial and fact-check gates.",
    defaultWorkflowName: "article-pipeline",
    steps: [
      { step_id: "research", title: "Research the topic, audience needs, and source constraints.", depends_on: [] },
      {
        step_id: "outline",
        title: "Build a clear article structure with sections and key arguments.",
        depends_on: ["research"]
      },
      {
        step_id: "draft",
        title: "Write the first full draft following outline and target tone.",
        depends_on: ["outline"]
      },
      {
        step_id: "edit",
        title: "Edit for clarity, flow, and style consistency.",
        depends_on: ["draft"]
      },
      {
        step_id: "fact-check",
        title: "Validate claims, numbers, and references before publication.",
        depends_on: ["edit"]
      },
      {
        step_id: "final",
        title: "Produce final publication-ready article output.",
        depends_on: ["fact-check"]
      }
    ]
  },
  {
    id: "social-pipeline",
    label: "Social pipeline",
    scenario: "Generate social content variants with hook iteration and QA before final delivery.",
    defaultWorkflowName: "social-pipeline",
    steps: [
      { step_id: "ideas", title: "Generate post ideas aligned to campaign objective.", depends_on: [] },
      {
        step_id: "hooks",
        title: "Create strong hooks for top ideas across target channels.",
        depends_on: ["ideas"]
      },
      {
        step_id: "variants",
        title: "Produce multiple post variants with CTA and format adaptation.",
        depends_on: ["hooks"]
      },
      {
        step_id: "qa",
        title: "Check policy, tone, and clarity across all variants.",
        depends_on: ["variants"]
      },
      {
        step_id: "final",
        title: "Select and deliver final approved post set.",
        depends_on: ["qa"]
      }
    ]
  },
  {
    id: "localization-pipeline",
    label: "Localization pipeline",
    scenario: "Adapt source text for a target locale with tone QA and final sign-off.",
    defaultWorkflowName: "localization-pipeline",
    steps: [
      { step_id: "source", title: "Ingest source content and localization requirements.", depends_on: [] },
      {
        step_id: "adapt",
        title: "Adapt messaging to locale, idioms, and cultural context.",
        depends_on: ["source"]
      },
      {
        step_id: "tone-qa",
        title: "Run tone and terminology QA against target audience expectations.",
        depends_on: ["adapt"]
      },
      {
        step_id: "final",
        title: "Deliver final localized version for publication.",
        depends_on: ["tone-qa"]
      }
    ]
  }
];
const WORKFLOW_PRESET_BY_ID: Record<WorkflowPresetId, WorkflowPreset> = WORKFLOW_PRESETS.reduce(
  (mapping, preset) => {
    mapping[preset.id] = preset;
    return mapping;
  },
  {} as Record<WorkflowPresetId, WorkflowPreset>
);

function workflowPresetToDrafts(preset: WorkflowPreset, defaultRoleId: number | null): WorkflowStepDraft[] {
  return preset.steps.map((step, index) => ({
    ...createWorkflowStepDraft(defaultRoleId, index),
    step_id: step.step_id,
    prompt: step.title,
    depends_on: [...step.depends_on]
  }));
}

function toSafeNumber(value: unknown): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return null;
  }
  return value;
}

function formatDurationMs(value: number | null): string {
  if (value === null || value < 0) {
    return "-";
  }
  const seconds = Math.round(value / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}

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
  const [selectedWorkflowPresetId, setSelectedWorkflowPresetId] = useState<WorkflowPresetId>(DEFAULT_WORKFLOW_PRESET_ID);
  const [workflowEditorMode, setWorkflowEditorMode] = useState<WorkflowEditorMode>("quick");
  const [workflowStepDrafts, setWorkflowStepDrafts] = useState<WorkflowStepDraft[]>(
    workflowStepsToDrafts(DEFAULT_WORKFLOW_STEPS as unknown as Record<string, unknown>[])
  );
  const [workflows, setWorkflows] = useState<WorkflowTemplateRead[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | null>(null);
  const [workflowQuickLaunchTemplateIdInput, setWorkflowQuickLaunchTemplateIdInput] = useState("");
  const [workflowQuickLaunchInitiatedBy, setWorkflowQuickLaunchInitiatedBy] = useState("ui-workflow-quick-launch");
  const [runWorkflowTemplateIdInput, setRunWorkflowTemplateIdInput] = useState("");
  const [runTaskIdsInput, setRunTaskIdsInput] = useState("");
  const [runInitiatedBy, setRunInitiatedBy] = useState("ui");
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunRead[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<EventRead[]>([]);
  const [runDispatchResult, setRunDispatchResult] = useState<WorkflowRunDispatchReadyResponse | null>(null);
  const [runPartialRerunResult, setRunPartialRerunResult] = useState<WorkflowRunPartialRerunResponse | null>(null);

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
  const [globalSearchInput, setGlobalSearchInput] = useState("");
  const [contextProjectId, setContextProjectId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedRole = useMemo(
    () => roles.find((item) => item.id === selectedRoleId) ?? null,
    [roles, selectedRoleId]
  );
  const selectedRun = useMemo(
    () => workflowRuns.find((item) => item.id === selectedRunId) ?? null,
    [workflowRuns, selectedRunId]
  );
  const selectedWorkflowPreset = useMemo(
    () => WORKFLOW_PRESET_BY_ID[selectedWorkflowPresetId] ?? WORKFLOW_PRESETS[0],
    [selectedWorkflowPresetId]
  );
  const quickLaunchTemplateIdInputTrimmed = workflowQuickLaunchTemplateIdInput.trim();
  const parsedQuickLaunchTemplateId =
    quickLaunchTemplateIdInputTrimmed.length === 0 ? null : Number(quickLaunchTemplateIdInputTrimmed);
  const hasQuickLaunchTemplateInputError =
    quickLaunchTemplateIdInputTrimmed.length > 0 &&
    parsedQuickLaunchTemplateId !== null &&
    Number.isNaN(parsedQuickLaunchTemplateId);
  const resolvedQuickLaunchTemplateId = hasQuickLaunchTemplateInputError
    ? null
    : quickLaunchTemplateIdInputTrimmed.length === 0
      ? selectedWorkflowId
      : parsedQuickLaunchTemplateId;
  const roleNameById = useMemo(() => {
    const mapping: Record<number, string> = {};
    roles.forEach((role) => {
      mapping[role.id] = role.name;
    });
    return mapping;
  }, [roles]);
  const projectNameById = useMemo(() => {
    const mapping: Record<number, string> = {};
    projects.forEach((project) => {
      mapping[project.id] = project.name;
    });
    return mapping;
  }, [projects]);
  const workflowNameById = useMemo(() => {
    const mapping: Record<number, string> = {};
    workflows.forEach((workflow) => {
      mapping[workflow.id] = workflow.name;
    });
    return mapping;
  }, [workflows]);
  const workflowProjectIdById = useMemo(() => {
    const mapping: Record<number, number | null> = {};
    workflows.forEach((workflow) => {
      mapping[workflow.id] = workflow.project_id;
    });
    return mapping;
  }, [workflows]);
  const taskById = useMemo(() => {
    const mapping: Record<number, TaskRead> = {};
    tasks.forEach((item) => {
      mapping[item.id] = item;
    });
    return mapping;
  }, [tasks]);
  const mergedTaskQuery = `${taskSearchInput} ${globalSearchInput}`.trim().toLowerCase();
  const filteredTasks = useMemo(() => {
    return tasks.filter((item) => {
      if (contextProjectId !== null && item.project_id !== contextProjectId) {
        return false;
      }
      if (mergedTaskQuery.length === 0) {
        return true;
      }
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
      return haystack.includes(mergedTaskQuery);
    });
  }, [contextProjectId, mergedTaskQuery, tasks]);
  const mergedRunQuery = `${runSearchInput} ${globalSearchInput}`.trim().toLowerCase();
  const filteredRuns = useMemo(() => {
    return workflowRuns.filter((item) => {
      const runProjectId =
        item.workflow_template_id === null ? null : (workflowProjectIdById[item.workflow_template_id] ?? null);
      if (contextProjectId !== null && runProjectId !== contextProjectId) {
        return false;
      }
      if (mergedRunQuery.length === 0) {
        return true;
      }
      const haystack = [
        String(item.id),
        item.status,
        item.initiated_by ?? "",
        item.workflow_template_id === null ? "" : String(item.workflow_template_id),
        item.task_ids.join(","),
        item.workflow_template_id === null ? "" : (workflowNameById[item.workflow_template_id] ?? ""),
        runProjectId === null ? "" : (projectNameById[runProjectId] ?? "")
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(mergedRunQuery);
    });
  }, [contextProjectId, mergedRunQuery, projectNameById, workflowNameById, workflowProjectIdById, workflowRuns]);
  const selectedApproval = useMemo(
    () => approvals.find((item) => item.id === selectedApprovalId) ?? taskApproval,
    [approvals, selectedApprovalId, taskApproval]
  );
  const sortedApprovals = useMemo(() => {
    const priority = (status: ApprovalStatus): number => {
      if (status === "pending") {
        return 0;
      }
      if (status === "rejected") {
        return 1;
      }
      return 2;
    };
    return [...approvals].sort((left, right) => {
      const byStatus = priority(left.status) - priority(right.status);
      if (byStatus !== 0) {
        return byStatus;
      }
      return right.id - left.id;
    });
  }, [approvals]);
  const pendingApprovalsCount = useMemo(
    () => approvals.filter((item) => item.status === "pending").length,
    [approvals]
  );
  const pendingApprovals = useMemo(
    () => sortedApprovals.filter((item) => item.status === "pending"),
    [sortedApprovals]
  );
  const filteredApprovals = useMemo(() => {
    return sortedApprovals.filter((approval) => {
      const approvalTask = taskById[approval.task_id] ?? null;
      if (contextProjectId !== null && approvalTask?.project_id !== contextProjectId) {
        return false;
      }
      const query = globalSearchInput.trim().toLowerCase();
      if (query.length === 0) {
        return true;
      }
      const haystack = [
        String(approval.id),
        String(approval.task_id),
        approval.status,
        approval.decided_by ?? "",
        approval.comment ?? "",
        approvalTask?.title ?? "",
        approvalTask?.status ?? ""
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [contextProjectId, globalSearchInput, sortedApprovals, taskById]);
  const failedRuns = useMemo(
    () => workflowRuns.filter((item) => item.status === "failed" || item.status === "aborted"),
    [workflowRuns]
  );
  const failedTasks = useMemo(
    () => tasks.filter((item) => item.status === "failed" || item.status === "submit-failed"),
    [tasks]
  );
  const runMetricsSummary = useMemo(() => {
    const durationValues = workflowRuns
      .map((run) => toSafeNumber(run.duration_ms))
      .filter((value): value is number => value !== null);
    const successRateValues = workflowRuns
      .map((run) => toSafeNumber(run.success_rate))
      .filter((value): value is number => value !== null);
    const retriesTotal = workflowRuns.reduce((total, run) => {
      const retries = toSafeNumber(run.retries_total);
      return total + (retries ?? 0);
    }, 0);

    const averageDurationMs =
      durationValues.length > 0
        ? Math.round(durationValues.reduce((total, value) => total + value, 0) / durationValues.length)
        : null;
    const averageSuccessRate =
      successRateValues.length > 0
        ? successRateValues.reduce((total, value) => total + value, 0) / successRateValues.length
        : 0;

    return {
      averageDurationLabel: formatDurationMs(averageDurationMs),
      averageSuccessRateLabel: formatPercentage(averageSuccessRate),
      retriesTotal
    };
  }, [workflowRuns]);
  const selectedRunTasks = useMemo(() => {
    if (!selectedRun) {
      return [];
    }
    return selectedRun.task_ids
      .map((id) => taskById[id])
      .filter((item): item is TaskRead => item !== undefined);
  }, [selectedRun, taskById]);
  const workflowStepsJsonParse = useMemo(
    () => parseWorkflowStepsJson(workflowStepsJson),
    [workflowStepsJson]
  );
  const workflowJsonValidationState = useMemo(() => {
    if (workflowStepsJsonParse.error || !workflowStepsJsonParse.steps) {
      return {
        hasErrors: true,
        summaryMessages: workflowStepsJsonParse.error ? [workflowStepsJsonParse.error] : []
      };
    }

    const drafts = workflowStepsToDrafts(workflowStepsJsonParse.steps);
    const validation = validateWorkflowStepDrafts(drafts);

    return {
      hasErrors: validation.hasErrors,
      summaryMessages: collectWorkflowValidationSummary(
        drafts,
        validation.formErrors,
        validation.stepErrorsByClientId
      )
    };
  }, [workflowStepsJsonParse]);
  const workflowQuickValidation = useMemo(
    () => validateWorkflowStepDrafts(workflowStepDrafts),
    [workflowStepDrafts]
  );
  const workflowQuickValidationSummary = useMemo(
    () =>
      collectWorkflowValidationSummary(
        workflowStepDrafts,
        workflowQuickValidation.formErrors,
        workflowQuickValidation.stepErrorsByClientId
      ),
    [workflowQuickValidation, workflowStepDrafts]
  );
  const activeWorkflowValidationSummary =
    workflowEditorMode === "quick" ? workflowQuickValidationSummary : workflowJsonValidationState.summaryMessages;
  const canSubmitWorkflow =
    workflowEditorMode === "quick" ? !workflowQuickValidation.hasErrors : !workflowJsonValidationState.hasErrors;
  const defaultWorkflowRoleId = roles.length > 0 ? roles[0].id : null;
  const canQuickLaunchWorkflow = resolvedQuickLaunchTemplateId !== null;

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
    setWorkflowStepsJson(stepsToJson(workflow.steps as unknown as Record<string, unknown>[]));
    setWorkflowStepDrafts(workflowStepsToDrafts(workflow.steps as unknown as Record<string, unknown>[]));
    setWorkflowQuickLaunchTemplateIdInput(String(workflow.id));
    setRunWorkflowTemplateIdInput(String(workflow.id));
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

  function applyWorkflowStepDrafts(nextDrafts: WorkflowStepDraft[]) {
    setWorkflowStepDrafts(nextDrafts);
    setWorkflowStepsJson(stepsToJson(workflowDraftsToSteps(nextDrafts)));
  }

  function onApplySelectedWorkflowPreset() {
    if (defaultWorkflowRoleId === null) {
      setError("Create at least one role before applying workflow presets.");
      return;
    }
    setSelectedWorkflowId(null);
    setWorkflowName(selectedWorkflowPreset.defaultWorkflowName);
    setWorkflowProjectIdInput("");
    setWorkflowEditorMode("quick");
    setError(null);
    applyWorkflowStepDrafts(workflowPresetToDrafts(selectedWorkflowPreset, defaultWorkflowRoleId));
  }

  function onWorkflowEditorModeChange(nextMode: WorkflowEditorMode) {
    if (nextMode === workflowEditorMode) {
      return;
    }
    if (nextMode === "quick") {
      if (workflowStepsJsonParse.error || !workflowStepsJsonParse.steps) {
        setError("Steps JSON must be valid before switching to Quick create.");
        return;
      }
      setWorkflowStepDrafts(workflowStepsToDrafts(workflowStepsJsonParse.steps));
    }
    setError(null);
    setWorkflowEditorMode(nextMode);
  }

  function onWorkflowStepDraftChange(clientId: string, patch: Partial<WorkflowStepDraft>) {
    applyWorkflowStepDrafts(
      workflowStepDrafts.map((draft) => {
        if (draft.client_id !== clientId) {
          return draft;
        }
        return { ...draft, ...patch };
      })
    );
  }

  function onWorkflowDependencyToggle(clientId: string, dependency: string, selected: boolean) {
    applyWorkflowStepDrafts(
      workflowStepDrafts.map((draft) => {
        if (draft.client_id !== clientId) {
          return draft;
        }
        const existing = draft.depends_on.filter((item) => item !== dependency);
        const depends_on = selected ? [...existing, dependency] : existing;
        return { ...draft, depends_on };
      })
    );
  }

  function onWorkflowStepsJsonChange(nextValue: string) {
    setWorkflowStepsJson(nextValue);
    const parsed = parseWorkflowStepsJson(nextValue);
    if (!parsed.error && parsed.steps) {
      setWorkflowStepDrafts(workflowStepsToDrafts(parsed.steps));
    }
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
      setRunDispatchResult(null);
      setRunPartialRerunResult(null);
      await loadTimelineEvents(created.id, null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onQuickLaunchWorkflowRun(event: FormEvent) {
    event.preventDefault();
    if (hasQuickLaunchTemplateInputError) {
      setError("Quick launch template ID must be a number.");
      return;
    }
    if (resolvedQuickLaunchTemplateId === null) {
      setError("Select a workflow template or enter a template ID for quick launch.");
      return;
    }
    setError(null);
    try {
      const created = await apiPost<WorkflowRunRead>("/workflow-runs", {
        workflow_template_id: resolvedQuickLaunchTemplateId,
        task_ids: [],
        initiated_by: workflowQuickLaunchInitiatedBy.trim() === "" ? null : workflowQuickLaunchInitiatedBy.trim()
      });
      setRunWorkflowTemplateIdInput(String(resolvedQuickLaunchTemplateId));
      setTaskFilterRunIdInput(String(created.id));
      setActiveTab("runs");
      await loadWorkflowRuns();
      setSelectedRunId(created.id);
      setRunDispatchResult(null);
      setRunPartialRerunResult(null);
      await loadTasks(created.id);
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
      setRunDispatchResult(null);
      setRunPartialRerunResult(null);
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
      setRunPartialRerunResult(null);
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

  async function onPartialRerun(payload: WorkflowRunPartialRerunRequest) {
    if (selectedRunId === null) {
      return;
    }
    setError(null);
    try {
      const result = await apiPost<WorkflowRunPartialRerunResponse>(
        `/workflow-runs/${selectedRunId}/partial-rerun`,
        payload
      );
      setRunPartialRerunResult(result);
      setRunDispatchResult(null);
      await loadWorkflowRuns();
      await loadTasks(selectedRunId);
      const lastSpawnedTaskId = result.spawn.length > 0 ? result.spawn[result.spawn.length - 1].task_id : null;
      if (lastSpawnedTaskId !== null) {
        const currentTask = await apiGet<TaskRead>(`/tasks/${lastSpawnedTaskId}`);
        setTask(currentTask);
        if (currentTask.requires_approval) {
          await loadTaskApproval(currentTask.id);
        } else {
          setTaskApproval(null);
        }
        try {
          const currentAudit = await apiGet<TaskAudit>(`/tasks/${lastSpawnedTaskId}/audit`);
          setAudit(currentAudit);
        } catch (auditError) {
          if (!isApiErrorWithStatus(auditError, 404)) {
            throw auditError;
          }
          setAudit(null);
        }
      }
      await loadTimelineEvents(selectedRunId, null);
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
    if (!canSubmitWorkflow) {
      setError("Fix workflow step validation errors before creating.");
      return;
    }
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
    if (!canSubmitWorkflow) {
      setError("Fix workflow step validation errors before updating.");
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
        setWorkflowQuickLaunchTemplateIdInput("");
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
      <div className="flex min-h-screen w-full">
        <AdminSidebar
          activeTab={activeTab}
          pendingApprovalsCount={pendingApprovalsCount}
          failedRunsCount={failedRuns.length}
          onChangeTab={setActiveTab}
        />

        <div className="flex min-h-screen flex-1 flex-col">
          <AdminTopBar
            apiBase={API_BASE}
            projects={projects}
            contextProjectId={contextProjectId}
            globalSearchInput={globalSearchInput}
            labelClass={labelClass}
            inputClass={inputClass}
            buttonClass={buttonClass}
            primaryButtonClass={primaryButtonClass}
            onSetContextProjectId={setContextProjectId}
            onSetGlobalSearchInput={setGlobalSearchInput}
            onChangeTab={setActiveTab}
            onRefreshAll={() => void onRefreshAll()}
          />

          <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
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

            <nav className="mb-6 flex flex-wrap gap-2 lg:hidden">
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
          <OverviewSection
            sectionClass={sectionClass}
            labelClass={labelClass}
            selectedRunLabel={selectedRun ? `${selectedRun.id} (${selectedRun.status})` : "none"}
            selectedTaskLabel={task ? `${task.id} (${task.status})` : "none"}
            selectedApprovalLabel={selectedApproval ? `${selectedApproval.id} (${selectedApproval.status})` : "none"}
            pendingApprovalsCount={pendingApprovals.length}
            failedRunsCount={failedRuns.length}
            failedTasksCount={failedTasks.length}
            averageRunDurationLabel={runMetricsSummary.averageDurationLabel}
            averageRunSuccessRateLabel={runMetricsSummary.averageSuccessRateLabel}
            totalRunRetries={runMetricsSummary.retriesTotal}
            pendingApprovalsPreview={pendingApprovals}
            onOpenApprovals={() => setActiveTab("approvals")}
            onOpenRuns={() => setActiveTab("runs")}
            onOpenApprovalById={(approvalId) => {
              const approval = approvals.find((item) => item.id === approvalId);
              if (approval) {
                setSelectedApprovalId(approval.id);
                setTaskApproval(approval);
              }
              setActiveTab("approvals");
            }}
          />
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
              <label>
                <span className={labelClass}>Preset</span>
                <select
                  className={inputClass}
                  value={selectedWorkflowPresetId}
                  onChange={(event) => setSelectedWorkflowPresetId(event.target.value as WorkflowPresetId)}
                >
                  {WORKFLOW_PRESETS.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="flex flex-wrap items-end gap-2">
                <button type="submit" className={primaryButtonClass} disabled={!canSubmitWorkflow}>Create</button>
                <button type="button" className={buttonClass} onClick={onUpdateWorkflow} disabled={selectedWorkflowId === null || !canSubmitWorkflow}>Update selected</button>
                <button type="button" className={buttonClass} onClick={onDeleteWorkflow} disabled={selectedWorkflowId === null}>Delete selected</button>
                <button type="button" className={buttonClass} onClick={() => void loadWorkflows()}>Refresh</button>
              </div>
              <div className="md:col-span-2 xl:col-span-4 rounded-lg border border-slate-200 bg-blue-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className={labelClass}>Preset scenario</p>
                    <p className="mt-1 text-sm text-slate-700">{selectedWorkflowPreset.scenario}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Step chain: {selectedWorkflowPreset.steps.map((step) => step.step_id).join(" -> ")}
                    </p>
                  </div>
                  <button type="button" className={buttonClass} onClick={onApplySelectedWorkflowPreset}>
                    Apply preset
                  </button>
                </div>
              </div>
              <div className="md:col-span-2 xl:col-span-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={labelClass}>Workflow steps</span>
                  <div className="inline-flex rounded-lg border border-slate-300 bg-white p-1">
                    <button
                      type="button"
                      onClick={() => onWorkflowEditorModeChange("quick")}
                      className={
                        workflowEditorMode === "quick"
                          ? "rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white"
                          : "rounded-md px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                      }
                    >
                      Quick create
                    </button>
                    <button
                      type="button"
                      onClick={() => onWorkflowEditorModeChange("json")}
                      className={
                        workflowEditorMode === "json"
                          ? "rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white"
                          : "rounded-md px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                      }
                    >
                      Raw JSON
                    </button>
                  </div>
                </div>

                {workflowEditorMode === "quick" ? (
                  <div className="mt-3 space-y-3">
                    <p className="text-xs text-slate-500">
                      Quick create edits `id`, `role`, `prompt`, and `depends_on`; prompt maps to API field `title`.
                    </p>
                    {workflowQuickValidationSummary.length > 0 && (
                      <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                        <p className="font-semibold">Validation summary ({workflowQuickValidationSummary.length})</p>
                        {workflowQuickValidationSummary.map((item, index) => (
                          <p key={`${item}-${index}`}>{item}</p>
                        ))}
                      </div>
                    )}
                    {workflowStepDrafts.map((draft, index) => {
                      const stepErrors = workflowQuickValidation.stepErrorsByClientId[draft.client_id] ?? {};
                      const cardErrorMessages = collectStepErrorMessages(stepErrors);
                      const dependencyOptions = workflowStepDrafts
                        .filter((candidate) => candidate.client_id !== draft.client_id)
                        .map((candidate) => candidate.step_id.trim())
                        .filter((candidate, candidateIndex, all) => candidate.length > 0 && all.indexOf(candidate) === candidateIndex);

                      return (
                        <div
                          key={draft.client_id}
                          className={`rounded-lg border bg-white p-3 ${
                            cardErrorMessages.length > 0 ? "border-rose-300" : "border-slate-200"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-slate-800">Step {index + 1}</p>
                            <button
                              type="button"
                              className={buttonClass}
                              onClick={() =>
                                applyWorkflowStepDrafts(
                                  workflowStepDrafts.filter((candidate) => candidate.client_id !== draft.client_id)
                                )
                              }
                            >
                              Remove
                            </button>
                          </div>
                          {cardErrorMessages.length > 0 && (
                            <div className="mt-2 rounded-md border border-rose-200 bg-rose-50 px-2 py-2 text-xs text-rose-700">
                              {cardErrorMessages.map((message, errorIndex) => (
                                <p key={`${draft.client_id}-card-error-${errorIndex}`}>{message}</p>
                              ))}
                            </div>
                          )}

                          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                            <label>
                              <span className={labelClass}>Step id</span>
                              <input
                                className={inputClass}
                                value={draft.step_id}
                                onChange={(e) => onWorkflowStepDraftChange(draft.client_id, { step_id: e.target.value })}
                                placeholder="plan"
                              />
                              {stepErrors.step_id && <p className="mt-1 text-xs text-rose-700">{stepErrors.step_id}</p>}
                            </label>

                            <label>
                              <span className={labelClass}>Role</span>
                              <select
                                className={inputClass}
                                value={draft.role_id === null ? "" : String(draft.role_id)}
                                onChange={(e) => {
                                  const nextRoleId = e.target.value === "" ? null : Number(e.target.value);
                                  onWorkflowStepDraftChange(draft.client_id, { role_id: Number.isNaN(nextRoleId) ? null : nextRoleId });
                                }}
                              >
                                <option value="">select role</option>
                                {roles.map((role) => (
                                  <option key={role.id} value={String(role.id)}>
                                    {role.id}: {role.name}
                                  </option>
                                ))}
                              </select>
                              {stepErrors.role_id && <p className="mt-1 text-xs text-rose-700">{stepErrors.role_id}</p>}
                            </label>

                            <label className="md:col-span-2 xl:col-span-2">
                              <span className={labelClass}>Prompt</span>
                              <textarea
                                className={textareaClass}
                                rows={3}
                                value={draft.prompt}
                                onChange={(e) => onWorkflowStepDraftChange(draft.client_id, { prompt: e.target.value })}
                                placeholder="Describe the work for this step."
                              />
                              {stepErrors.prompt && <p className="mt-1 text-xs text-rose-700">{stepErrors.prompt}</p>}
                            </label>

                            <fieldset className="md:col-span-2 xl:col-span-4">
                              <legend className={labelClass}>Depends on</legend>
                              {dependencyOptions.length === 0 ? (
                                <p className="mt-2 text-xs text-slate-500">No other step IDs available yet.</p>
                              ) : (
                                <div className="mt-2 flex flex-wrap gap-2">
                                  {dependencyOptions.map((dependency) => (
                                    <label
                                      key={dependency}
                                      className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700"
                                    >
                                      <input
                                        type="checkbox"
                                        checked={draft.depends_on.includes(dependency)}
                                        onChange={(e) => onWorkflowDependencyToggle(draft.client_id, dependency, e.target.checked)}
                                      />
                                      <span>{dependency}</span>
                                    </label>
                                  ))}
                                </div>
                              )}
                              {stepErrors.depends_on && <p className="mt-1 text-xs text-rose-700">{stepErrors.depends_on}</p>}
                            </fieldset>
                          </div>
                        </div>
                      );
                    })}

                    <button
                      type="button"
                      className={buttonClass}
                      onClick={() =>
                        applyWorkflowStepDrafts([
                          ...workflowStepDrafts,
                          createWorkflowStepDraft(defaultWorkflowRoleId, workflowStepDrafts.length)
                        ])
                      }
                    >
                      Add step
                    </button>
                  </div>
                ) : (
                  <div className="mt-3 space-y-3">
                    {activeWorkflowValidationSummary.length > 0 && (
                      <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                        <p className="font-semibold">Validation summary ({activeWorkflowValidationSummary.length})</p>
                        {activeWorkflowValidationSummary.map((item, index) => (
                          <p key={`${item}-${index}`}>{item}</p>
                        ))}
                      </div>
                    )}
                    <label className="block">
                      <span className={labelClass}>Steps JSON</span>
                      <textarea
                        className={textareaClass}
                        rows={10}
                        value={workflowStepsJson}
                        onChange={(e) => onWorkflowStepsJsonChange(e.target.value)}
                      />
                      {workflowStepsJsonParse.error && (
                        <p className="mt-1 text-xs text-rose-700">{workflowStepsJsonParse.error}</p>
                      )}
                    </label>
                  </div>
                )}
              </div>
            </form>

            <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onQuickLaunchWorkflowRun}>
              <div className="md:col-span-2 xl:col-span-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">Quick launch</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Start a run directly from this page. Leave template ID empty to use the selected template row.
                    </p>
                  </div>
                  <button type="submit" className={primaryButtonClass} disabled={!canQuickLaunchWorkflow}>
                    Launch run
                  </button>
                </div>
              </div>
              <label>
                <span className={labelClass}>Template ID</span>
                <input
                  className={inputClass}
                  value={workflowQuickLaunchTemplateIdInput}
                  onChange={(event) => setWorkflowQuickLaunchTemplateIdInput(event.target.value)}
                  placeholder={selectedWorkflowId === null ? "required if no row selected" : `selected: ${selectedWorkflowId}`}
                />
                {hasQuickLaunchTemplateInputError && (
                  <p className="mt-1 text-xs text-rose-700">Template ID must be a number.</p>
                )}
              </label>
              <label>
                <span className={labelClass}>Initiated by</span>
                <input
                  className={inputClass}
                  value={workflowQuickLaunchInitiatedBy}
                  onChange={(event) => setWorkflowQuickLaunchInitiatedBy(event.target.value)}
                  placeholder="optional"
                />
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
          <RunsCenterSection
            sectionClass={sectionClass}
            labelClass={labelClass}
            inputClass={inputClass}
            buttonClass={buttonClass}
            primaryButtonClass={primaryButtonClass}
            tableClass={tableClass}
            thClass={thClass}
            tdClass={tdClass}
            runWorkflowTemplateIdInput={runWorkflowTemplateIdInput}
            runTaskIdsInput={runTaskIdsInput}
            runInitiatedBy={runInitiatedBy}
            runSearchInput={runSearchInput}
            selectedRunId={selectedRunId}
            filteredRuns={filteredRuns}
            roleNameById={roleNameById}
            workflowNameById={workflowNameById}
            workflowProjectIdById={workflowProjectIdById}
            projectNameById={projectNameById}
            selectedRun={selectedRun}
            selectedRunTasks={selectedRunTasks}
            runDispatchResult={runDispatchResult}
            runPartialRerunResult={runPartialRerunResult}
            timelineEvents={timelineEvents}
            onRunWorkflowTemplateIdChange={setRunWorkflowTemplateIdInput}
            onRunTaskIdsChange={setRunTaskIdsInput}
            onRunInitiatedByChange={setRunInitiatedBy}
            onRunSearchChange={setRunSearchInput}
            onCreateWorkflowRun={onCreateWorkflowRun}
            onRefreshRuns={() => void loadWorkflowRuns()}
            onRefreshTimeline={() => void onRefreshTimeline()}
            onRunAction={(action) => void onRunAction(action)}
            onDispatchReadyTask={onDispatchReadyTask}
            onPartialRerun={(payload) => void onPartialRerun(payload)}
            onSelectRun={(runId) => {
              setSelectedRunId(runId);
              setTaskFilterRunIdInput(String(runId));
              setRunDispatchResult(null);
              setRunPartialRerunResult(null);
              void loadTasks(runId);
              void loadTimelineEvents(runId, null);
            }}
          />
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
          <ApprovalsSection
            sectionClass={sectionClass}
            labelClass={labelClass}
            inputClass={inputClass}
            buttonClass={buttonClass}
            primaryButtonClass={primaryButtonClass}
            tableClass={tableClass}
            thClass={thClass}
            tdClass={tdClass}
            approvalLookupIdInput={approvalLookupIdInput}
            approvalActor={approvalActor}
            approvalComment={approvalComment}
            pendingApprovalsCount={pendingApprovals.length}
            filteredApprovalsCount={filteredApprovals.length}
            filteredApprovals={filteredApprovals}
            selectedApproval={selectedApproval}
            onApprovalLookupIdChange={setApprovalLookupIdInput}
            onApprovalActorChange={setApprovalActor}
            onApprovalCommentChange={setApprovalComment}
            onRefreshApprovals={() => void refreshApprovals()}
            onLookupApprovalById={() => void onLookupApprovalById()}
            onApprovalDecision={(action) => void onApprovalDecision(action)}
            onSelectApproval={(approval) => {
              setSelectedApprovalId(approval.id);
              setTaskApproval(approval);
            }}
          />
        )}
          </div>
        </div>
      </div>
    </main>
  );
}
