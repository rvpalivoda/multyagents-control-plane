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
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">Select a run from the left table.</p>
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
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {runDispatchResult && (
            <pre className="max-h-44 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
              {JSON.stringify(runDispatchResult, null, 2)}
            </pre>
          )}
          <pre className="max-h-64 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            {JSON.stringify(timelineEvents, null, 2)}
          </pre>
        </div>
      </div>
    </section>
  );
}
