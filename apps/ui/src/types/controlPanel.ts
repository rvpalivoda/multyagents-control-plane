import type { ApprovalStatus, TaskStatus } from "../../../../packages/contracts/ts/context7";

export type DispatchResult = {
  resolved_context7_enabled: boolean;
};

export type WorkflowRunDispatchReadyResponse = {
  run_id: number;
  dispatched: boolean;
  task_id: number | null;
  reason: string | null;
  dispatch: DispatchResult | null;
};

export type WorkflowRunDispatchPlanItem = {
  task_id: number;
  consumed_artifact_ids: number[];
};

export type WorkflowRunDispatchBlockedItem = {
  task_id: number | null;
  reason: string;
  details: Record<string, unknown>;
};

export type WorkflowRunDispatchPlan = {
  ready: WorkflowRunDispatchPlanItem[];
  blocked: WorkflowRunDispatchBlockedItem[];
};

export type WorkflowRunPartialRerunRequest = {
  task_ids: number[];
  step_ids: string[];
  requested_by: string;
  reason: string;
  auto_dispatch: boolean;
  max_dispatch: number;
};

export type WorkflowRunPartialRerunResponse = {
  run_id: number;
  requested_by: string;
  reason: string;
  selected_task_ids: number[];
  selected_step_ids: string[];
  reset_task_ids: number[];
  plan: WorkflowRunDispatchPlan;
  spawn: Array<{
    task_id: number;
    submitted: boolean;
    task_status: TaskStatus;
    error?: string | null;
  }>;
  aggregate: Record<string, unknown>;
};

export type WorkflowStep = {
  step_id: string;
  role_id: number;
  title: string;
  depends_on: string[];
  required_artifacts?: Array<{
    from_step_id?: string | null;
    artifact_type?: string | null;
    label?: string | null;
  }>;
};

export type WorkflowTemplateRead = {
  id: number;
  name: string;
  project_id: number | null;
  steps: WorkflowStep[];
};

export type ProjectRead = {
  id: number;
  name: string;
  root_path: string;
  allowed_paths: string[];
};

export type SkillPackRead = {
  id: number;
  name: string;
  skills: string[];
  used_by_role_ids: number[];
};

export type ApprovalRead = {
  id: number;
  task_id: number;
  status: ApprovalStatus;
  decided_by: string | null;
  comment: string | null;
};

export type UiTab =
  | "overview"
  | "projects"
  | "roles"
  | "skills"
  | "workflows"
  | "runs"
  | "tasks"
  | "approvals";

export const UI_TABS: Array<{ id: UiTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "projects", label: "Projects" },
  { id: "roles", label: "Roles" },
  { id: "skills", label: "Skill Packs" },
  { id: "workflows", label: "Workflows" },
  { id: "runs", label: "Runs" },
  { id: "tasks", label: "Tasks" },
  { id: "approvals", label: "Approvals" }
];
