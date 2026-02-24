import type { ApprovalRead } from "../types/controlPanel";

type ApprovalsSectionProps = {
  sectionClass: string;
  labelClass: string;
  inputClass: string;
  buttonClass: string;
  primaryButtonClass: string;
  tableClass: string;
  thClass: string;
  tdClass: string;
  approvalLookupIdInput: string;
  approvalActor: string;
  approvalComment: string;
  pendingApprovalsCount: number;
  filteredApprovalsCount: number;
  filteredApprovals: ApprovalRead[];
  selectedApproval: ApprovalRead | null;
  onApprovalLookupIdChange: (value: string) => void;
  onApprovalActorChange: (value: string) => void;
  onApprovalCommentChange: (value: string) => void;
  onRefreshApprovals: () => void;
  onLookupApprovalById: () => void;
  onApprovalDecision: (action: "approve" | "reject") => void;
  onSelectApproval: (approval: ApprovalRead) => void;
};

export function ApprovalsSection(props: ApprovalsSectionProps) {
  const {
    sectionClass,
    labelClass,
    inputClass,
    buttonClass,
    primaryButtonClass,
    tableClass,
    thClass,
    tdClass,
    approvalLookupIdInput,
    approvalActor,
    approvalComment,
    pendingApprovalsCount,
    filteredApprovalsCount,
    filteredApprovals,
    selectedApproval,
    onApprovalLookupIdChange,
    onApprovalActorChange,
    onApprovalCommentChange,
    onRefreshApprovals,
    onLookupApprovalById,
    onApprovalDecision,
    onSelectApproval
  } = props;

  return (
    <section className={sectionClass}>
      <h2 className="text-lg font-semibold">Approvals Inbox</h2>
      <p className="mt-1 text-sm text-slate-500">Pending approvals are sorted first for faster operator decisions.</p>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="flex flex-wrap items-end gap-2">
          <button type="button" className={buttonClass} onClick={onRefreshApprovals}>
            Refresh approvals
          </button>
        </div>
        <label>
          <span className={labelClass}>Approval ID</span>
          <input className={inputClass} value={approvalLookupIdInput} onChange={(event) => onApprovalLookupIdChange(event.target.value)} />
        </label>
        <div className="flex items-end">
          <button type="button" className={buttonClass} onClick={onLookupApprovalById}>
            Load by ID
          </button>
        </div>
        <div />
        <label>
          <span className={labelClass}>Actor</span>
          <input className={inputClass} value={approvalActor} onChange={(event) => onApprovalActorChange(event.target.value)} />
        </label>
        <label className="md:col-span-2">
          <span className={labelClass}>Comment</span>
          <input className={inputClass} value={approvalComment} onChange={(event) => onApprovalCommentChange(event.target.value)} />
        </label>
        <div className="flex flex-wrap items-end gap-2">
          <button
            type="button"
            className={primaryButtonClass}
            onClick={() => onApprovalDecision("approve")}
            disabled={selectedApproval?.status !== "pending"}
          >
            Approve
          </button>
          <button
            type="button"
            className={buttonClass}
            onClick={() => onApprovalDecision("reject")}
            disabled={selectedApproval?.status !== "pending"}
          >
            Reject
          </button>
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        Pending: {pendingApprovalsCount} | Total in view: {filteredApprovalsCount}
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
            {filteredApprovals.map((approval) => (
              <tr
                key={approval.id}
                onClick={() => onSelectApproval(approval)}
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
  );
}
