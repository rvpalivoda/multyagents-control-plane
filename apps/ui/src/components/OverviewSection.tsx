import type { ApprovalRead } from "../types/controlPanel";

type OverviewSectionProps = {
  sectionClass: string;
  labelClass: string;
  selectedRunLabel: string;
  selectedTaskLabel: string;
  selectedApprovalLabel: string;
  pendingApprovalsCount: number;
  failedRunsCount: number;
  failedTasksCount: number;
  averageRunDurationLabel: string;
  averageRunSuccessRateLabel: string;
  totalRunRetries: number;
  pendingApprovalsPreview: ApprovalRead[];
  onOpenApprovals: () => void;
  onOpenRuns: () => void;
  onOpenApprovalById: (approvalId: number) => void;
};

export function OverviewSection(props: OverviewSectionProps) {
  const {
    sectionClass,
    labelClass,
    selectedRunLabel,
    selectedTaskLabel,
    selectedApprovalLabel,
    pendingApprovalsCount,
    failedRunsCount,
    failedTasksCount,
    averageRunDurationLabel,
    averageRunSuccessRateLabel,
    totalRunRetries,
    pendingApprovalsPreview,
    onOpenApprovals,
    onOpenRuns,
    onOpenApprovalById
  } = props;

  return (
    <section className={sectionClass}>
      <h2 className="text-lg font-semibold">Overview</h2>
      <p className="mt-1 text-sm text-slate-500">Operational snapshot and actions that need attention now.</p>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className={labelClass}>Selected run</p>
          <p className="mt-2 text-sm">{selectedRunLabel}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className={labelClass}>Selected task</p>
          <p className="mt-2 text-sm">{selectedTaskLabel}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className={labelClass}>Selected approval</p>
          <p className="mt-2 text-sm">{selectedApprovalLabel}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className={labelClass}>Run efficiency</p>
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            <li>Average duration: {averageRunDurationLabel}</li>
            <li>Average success rate: {averageRunSuccessRateLabel}</li>
            <li>Total retries: {totalRunRetries}</li>
          </ul>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className={labelClass}>Needs attention</p>
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            <li>Pending approvals: {pendingApprovalsCount}</li>
            <li>Failed runs: {failedRunsCount}</li>
            <li>Failed tasks: {failedTasksCount}</li>
          </ul>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={onOpenApprovals}>
              Open approvals
            </button>
            <button type="button" className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={onOpenRuns}>
              Open runs
            </button>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className={labelClass}>Recent pending approvals</p>
          <div className="mt-2 space-y-1 text-sm text-slate-700">
            {pendingApprovalsPreview.slice(0, 5).map((approval) => (
              <button
                key={approval.id}
                type="button"
                className="block w-full rounded-md px-2 py-1 text-left hover:bg-white"
                onClick={() => onOpenApprovalById(approval.id)}
              >
                #{approval.id} - task {approval.task_id}
              </button>
            ))}
            {pendingApprovalsPreview.length === 0 && <p className="text-slate-500">No pending approvals.</p>}
          </div>
        </div>
      </div>
    </section>
  );
}
