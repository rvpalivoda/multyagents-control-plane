import type { UiTab } from "../types/controlPanel";
import { UI_TABS } from "../types/controlPanel";

type AdminSidebarProps = {
  activeTab: UiTab;
  pendingApprovalsCount: number;
  failedRunsCount: number;
  onChangeTab: (tab: UiTab) => void;
};

export function AdminSidebar(props: AdminSidebarProps) {
  const { activeTab, pendingApprovalsCount, failedRunsCount, onChangeTab } = props;

  return (
    <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white px-4 py-6 lg:flex lg:flex-col">
      <h1 className="text-xl font-semibold tracking-tight">Control Plane</h1>
      <p className="mt-1 text-xs text-slate-500">Operations Console</p>
      <nav className="mt-6 flex flex-col gap-2">
        {UI_TABS.map((tab) => {
          const active = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChangeTab(tab.id)}
              className={
                active
                  ? "w-full rounded-lg border border-blue-500 bg-blue-600 px-3 py-2 text-left text-sm font-medium text-white"
                  : "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm font-medium text-slate-700 hover:border-slate-300 hover:bg-slate-50"
              }
            >
              {tab.label}
            </button>
          );
        })}
      </nav>
      <div className="mt-6 space-y-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-500">Pending approvals</span>
          <div className="text-lg font-semibold">{pendingApprovalsCount}</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-500">Failed runs</span>
          <div className="text-lg font-semibold">{failedRunsCount}</div>
        </div>
      </div>
    </aside>
  );
}
