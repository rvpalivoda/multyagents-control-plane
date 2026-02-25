export type Context7Mode = "inherit" | "force_on" | "force_off";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type WorkflowRunStatus = "created" | "running" | "paused" | "aborted" | "success" | "failed";
export type TaskStatus =
  | "created"
  | "dispatched"
  | "queued"
  | "running"
  | "cancel-requested"
  | "success"
  | "failed"
  | "canceled"
  | "submit-failed";
export type ExecutionMode =
  | "no-workspace"
  | "shared-workspace"
  | "isolated-worktree"
  | "docker-sandbox";

export type RoleRead = {
  id: number;
  name: string;
  context7_enabled: boolean;
  system_prompt: string;
  allowed_tools: string[];
  skill_packs: string[];
  execution_constraints: Record<string, unknown>;
};

export type TaskRead = {
  id: number;
  role_id: number;
  title: string;
  context7_mode: Context7Mode;
  execution_mode: ExecutionMode;
  status: TaskStatus;
  requires_approval: boolean;
  project_id: number | null;
  lock_paths: string[];
  runner_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
};

export type TaskHandoffArtifactRef = {
  artifact_id: number;
  is_required: boolean;
  note: string | null;
};

export type TaskHandoffRead = {
  task_id: number;
  run_id: number | null;
  summary: string;
  details: string | null;
  next_actions: string[];
  open_questions: string[];
  artifacts: TaskHandoffArtifactRef[];
  created_at: string;
  updated_at: string;
};

export type TaskAudit = {
  task_id: number;
  role_id: number;
  context7_mode: Context7Mode;
  role_context7_enabled: boolean;
  resolved_context7_enabled: boolean;
  execution_mode: ExecutionMode;
  requires_approval: boolean;
  approval_status: ApprovalStatus | null;
  project_id: number | null;
  lock_paths: string[];
  handoff: TaskHandoffRead | null;
};

export type WorkflowRunRead = {
  id: number;
  workflow_template_id: number | null;
  task_ids: number[];
  status: WorkflowRunStatus;
  initiated_by: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowRunDispatchReadyResponse = {
  run_id: number;
  dispatched: boolean;
  task_id: number | null;
  reason: string | null;
  dispatch: Record<string, unknown> | null;
};

export type EventRead = {
  id: number;
  event_type: string;
  run_id: number | null;
  task_id: number | null;
  payload: Record<string, unknown>;
  created_at: string;
};
