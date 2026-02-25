import type { FormEvent } from "react";
import type { EventRead, TaskRead, WorkflowRunRead } from "../../../packages/contracts/ts/context7";
import type { WorkflowRunDispatchReadyResponse } from "../types/controlPanel";

type RunsCenterSectionProps = {
  sectionClass: string;
  labelClass: string;
  inputClass: string;
  buttonClass: string;
  primaryButtonClass: string;
  tableClass: string;
  thClass: string;
  tdClass: string;
  runWorkflowTemplateIdInput: string;
  runTaskIdsInput: string;
  runInitiatedBy: string;
  runSearchInput: string;
  selectedRunId: number | null;
  filteredRuns: WorkflowRunRead[];
  roleNameById: Record<number, string>;
  workflowNameById: Record<number, string>;
  workflowProjectIdById: Record<number, number | null>;
  projectNameById: Record<number, string>;
  selectedRun: WorkflowRunRead | null;
  selectedRunTasks: TaskRead[];
  runDispatchResult: WorkflowRunDispatchReadyResponse | null;
  timelineEvents: EventRead[];
  onRunWorkflowTemplateIdChange: (value: string) => void;
  onRunTaskIdsChange: (value: string) => void;
  onRunInitiatedByChange: (value: string) => void;
  onRunSearchChange: (value: string) => void;
  onCreateWorkflowRun: (event: FormEvent) => void;
  onRefreshRuns: () => void;
  onRefreshTimeline: () => void;
  onRunAction: (action: "pause" | "resume" | "abort") => void;
  onDispatchReadyTask: () => void;
  onSelectRun: (runId: number) => void;
};

type HandoffBoardItem = {
  eventId: number;
  taskId: number | null;
  createdAt: string;
  summary: string;
  details: string | null;
  nextActions: string[];
  openQuestions: string[];
  requiredArtifactIds: number[];
};

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function toNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is number => typeof item === "number");
}

function isFailedTaskStatus(status: TaskRead["status"]): boolean {
  return status === "failed" || status === "submit-failed" || status === "canceled";
}

function buildHandoffBoard(events: EventRead[]): HandoffBoardItem[] {
  const items = events
    .filter((event) => event.event_type === "task.handoff_published")
    .map((event) => {
      const payload = event.payload as Record<string, unknown>;
      const summaryRaw = payload["summary"];
      return {
        eventId: event.id,
        taskId: event.task_id,
        createdAt: event.created_at,
        summary: typeof summaryRaw === "string" ? summaryRaw : "",
        details: typeof payload["details"] === "string" ? payload["details"] : null,
        nextActions: toStringArray(payload["next_actions"]),
        openQuestions: toStringArray(payload["open_questions"]),
        requiredArtifactIds: toNumberArray(payload["required_artifact_ids"])
      };
    })
    .filter((item) => item.summary.length > 0);
  return items.sort((left, right) => left.eventId - right.eventId);
}

function formatDurationMs(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value) || value < 0) {
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

function formatPercentage(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return `${value.toFixed(1)}%`;
}

export function RunsCenterSection(props: RunsCenterSectionProps) {
  const {
    sectionClass,
    labelClass,
    inputClass,
    buttonClass,
    primaryButtonClass,
    tableClass,
    thClass,
    tdClass,
    runWorkflowTemplateIdInput,
    runTaskIdsInput,
    runInitiatedBy,
    runSearchInput,
    selectedRunId,
    filteredRuns,
    roleNameById,
    workflowNameById,
    workflowProjectIdById,
    projectNameById,
    selectedRun,
    selectedRunTasks,
    runDispatchResult,
    timelineEvents,
    onRunWorkflowTemplateIdChange,
    onRunTaskIdsChange,
    onRunInitiatedByChange,
    onRunSearchChange,
    onCreateWorkflowRun,
    onRefreshRuns,
    onRefreshTimeline,
    onRunAction,
    onDispatchReadyTask,
    onSelectRun
  } = props;
  const handoffBoard = buildHandoffBoard(timelineEvents);
  const failedRunTasks = selectedRunTasks.filter((runTask) => isFailedTaskStatus(runTask.status));
  const selectedRunFailureCategories = selectedRun?.failure_categories ?? [];
  const selectedRunFailureHints = selectedRun?.failure_triage_hints ?? [];
  const selectedRunSuggestedActions = selectedRun?.suggested_next_actions ?? [];

  return (
    <section className={sectionClass}>
      <h2 className="text-lg font-semibold">Runs Center</h2>
      <p className="mt-1 text-sm text-slate-500">Create, filter, and operate runs from one screen.</p>
      <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={onCreateWorkflowRun}>
        <label>
          <span className={labelClass}>Workflow template ID</span>
          <input
            className={inputClass}
            value={runWorkflowTemplateIdInput}
            onChange={(event) => onRunWorkflowTemplateIdChange(event.target.value)}
            placeholder="optional"
          />
        </label>
        <label>
          <span className={labelClass}>Task IDs (comma/newline)</span>
          <input
            className={inputClass}
            value={runTaskIdsInput}
            onChange={(event) => onRunTaskIdsChange(event.target.value)}
            placeholder="1,2"
          />
        </label>
        <label>
          <span className={labelClass}>Initiated by</span>
          <input className={inputClass} value={runInitiatedBy} onChange={(event) => onRunInitiatedByChange(event.target.value)} />
        </label>
        <label>
          <span className={labelClass}>Search runs</span>
          <input
            className={inputClass}
            value={runSearchInput}
            onChange={(event) => onRunSearchChange(event.target.value)}
            placeholder="id/status/template"
          />
        </label>
        <div className="md:col-span-2 xl:col-span-4 flex flex-wrap gap-2">
          <button type="submit" className={primaryButtonClass}>Create run</button>
          <button type="button" className={buttonClass} onClick={onRefreshRuns}>Refresh runs</button>
          <button type="button" className={buttonClass} onClick={onRefreshTimeline}>Refresh timeline</button>
          <button type="button" className={buttonClass} onClick={() => onRunAction("pause")} disabled={selectedRunId === null}>Pause run</button>
          <button type="button" className={buttonClass} onClick={() => onRunAction("resume")} disabled={selectedRunId === null}>Resume run</button>
          <button type="button" className={buttonClass} onClick={() => onRunAction("abort")} disabled={selectedRunId === null}>Abort run</button>
          <button type="button" className={buttonClass} onClick={onDispatchReadyTask} disabled={selectedRunId === null}>Dispatch ready task</button>
        </div>
      </form>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="xl:col-span-5">
          <div className="max-h-[560px] overflow-auto rounded-lg border border-slate-200 bg-white">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={thClass}>id</th>
                  <th className={thClass}>status</th>
                  <th className={thClass}>duration</th>
                  <th className={thClass}>success rate</th>
                  <th className={thClass}>retries</th>
                  <th className={thClass}>template</th>
                  <th className={thClass}>project</th>
                  <th className={thClass}>updated</th>
                </tr>
              </thead>
              <tbody>
                {filteredRuns.map((run) => {
                  const projectId = run.workflow_template_id === null ? null : (workflowProjectIdById[run.workflow_template_id] ?? null);
                  return (
                    <tr
                      key={run.id}
                      onClick={() => onSelectRun(run.id)}
                      className={`cursor-pointer ${run.id === selectedRunId ? "bg-blue-50" : "hover:bg-slate-50"}`}
                    >
                      <td className={tdClass}>{run.id}</td>
                      <td className={tdClass}>{run.status}</td>
                      <td className={tdClass}>{formatDurationMs(run.duration_ms)}</td>
                      <td className={tdClass}>{formatPercentage(run.success_rate)}</td>
                      <td className={tdClass}>{run.retries_total}</td>
                      <td className={tdClass}>
                        {run.workflow_template_id === null
                          ? "-"
                          : `${run.workflow_template_id} ${workflowNameById[run.workflow_template_id] ?? ""}`}
                      </td>
                      <td className={tdClass}>
                        {projectId === null ? "-" : `${projectId} ${projectNameById[projectId] ?? ""}`}
                      </td>
                      <td className={tdClass}>{run.updated_at}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="xl:col-span-7 space-y-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className={labelClass}>Selected run summary</p>
            {selectedRun ? (
              <div className="mt-2 text-sm text-slate-700">
                <p>
                  Run #{selectedRun.id} ({selectedRun.status})
                </p>
                <p>Template: {selectedRun.workflow_template_id ?? "-"}</p>
                <p>Tasks: {selectedRun.task_ids.join(", ") || "-"}</p>
                <p>Duration: {formatDurationMs(selectedRun.duration_ms)}</p>
                <p>Success rate: {formatPercentage(selectedRun.success_rate)}</p>
                <p>Retries: {selectedRun.retries_total}</p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">Select a run from the left table.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className={labelClass}>Per-role throughput</p>
            {selectedRun && selectedRun.per_role.length > 0 ? (
              <ul className="mt-2 space-y-1 text-sm text-slate-700">
                {selectedRun.per_role.map((metric) => (
                  <li key={metric.role_id}>
                    {roleNameById[metric.role_id] ?? `role ${metric.role_id}`}: throughput {metric.throughput_tasks}/
                    {metric.task_count}, success {formatPercentage(metric.success_rate)}, retries {metric.retries_total},
                    duration {formatDurationMs(metric.duration_ms)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-slate-500">No per-role metrics yet.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className={labelClass}>Tasks in selected run</p>
            <div className="mt-2 max-h-40 overflow-auto">
              {selectedRunTasks.length === 0 ? (
                <p className="text-sm text-slate-500">No task details loaded yet.</p>
              ) : (
                <ul className="space-y-1 text-sm text-slate-700">
                  {selectedRunTasks.map((runTask) => (
                    <li key={runTask.id}>
                      #{runTask.id} - {runTask.status} - {runTask.title}
                      {isFailedTaskStatus(runTask.status) && (
                        <div className="mt-1 rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                          <p>Category: {runTask.failure_category ?? "unknown"}</p>
                          {runTask.failure_triage_hints.length > 0 && (
                            <p>Hint: {runTask.failure_triage_hints[0]}</p>
                          )}
                          {runTask.suggested_next_actions.length > 0 && (
                            <p>Suggested next action: {runTask.suggested_next_actions[0]}</p>
                          )}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className={labelClass}>Failure triage</p>
            {!selectedRun ? (
              <p className="mt-2 text-sm text-slate-500">Select a run to see triage hints and suggested actions.</p>
            ) : selectedRunFailureCategories.length === 0 && failedRunTasks.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No failed tasks detected in this run.</p>
            ) : (
              <div className="mt-2 space-y-2 text-sm text-amber-900">
                <p>
                  Categories: {selectedRunFailureCategories.length > 0 ? selectedRunFailureCategories.join(", ") : "-"}
                </p>
                <p>Failed tasks: {failedRunTasks.map((task) => `#${task.id}`).join(", ") || "-"}</p>
                {selectedRunFailureHints.length > 0 && (
                  <p>Hints: {selectedRunFailureHints.join(" | ")}</p>
                )}
                {selectedRunSuggestedActions.length > 0 && (
                  <p>Suggested next actions: {selectedRunSuggestedActions.join(" | ")}</p>
                )}
              </div>
            )}
          </div>

          {runDispatchResult && (
            <pre className="max-h-44 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
              {JSON.stringify(runDispatchResult, null, 2)}
            </pre>
          )}

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className={labelClass}>Handoff board</p>
            {handoffBoard.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No handoff payloads in timeline yet.</p>
            ) : (
              <ul className="mt-2 space-y-2 text-sm text-slate-700">
                {handoffBoard.map((item) => (
                  <li key={item.eventId} className="rounded-md border border-slate-200 bg-white p-2">
                    <p className="font-medium">
                      Task #{item.taskId ?? "-"} at {item.createdAt}
                    </p>
                    <p className="mt-1">{item.summary}</p>
                    {item.details && <p className="mt-1 text-xs text-slate-600">{item.details}</p>}
                    {item.nextActions.length > 0 && (
                      <p className="mt-1 text-xs text-slate-600">Next actions: {item.nextActions.join(" | ")}</p>
                    )}
                    {item.openQuestions.length > 0 && (
                      <p className="mt-1 text-xs text-slate-600">Open questions: {item.openQuestions.join(" | ")}</p>
                    )}
                    <p className="mt-1 text-xs text-slate-600">
                      Required artifacts: {item.requiredArtifactIds.length > 0 ? item.requiredArtifactIds.join(", ") : "-"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <pre className="max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            {JSON.stringify(timelineEvents, null, 2)}
          </pre>
        </div>
      </div>
    </section>
  );
}
