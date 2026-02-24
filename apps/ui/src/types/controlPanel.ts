import type { ApprovalStatus } from "../../../packages/contracts/ts/context7";

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

export type WorkflowStep = {
  step_id: string;
  role_id: number;
  title: string;
  depends_on: string[];
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
