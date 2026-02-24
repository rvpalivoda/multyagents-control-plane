import type { ProjectRead, UiTab } from "../types/controlPanel";

type AdminTopBarProps = {
  apiBase: string;
  projects: ProjectRead[];
  contextProjectId: number | null;
  globalSearchInput: string;
  labelClass: string;
  inputClass: string;
  buttonClass: string;
  primaryButtonClass: string;
  onSetContextProjectId: (projectId: number | null) => void;
  onSetGlobalSearchInput: (value: string) => void;
  onChangeTab: (tab: UiTab) => void;
  onRefreshAll: () => void;
};

export function AdminTopBar(props: AdminTopBarProps) {
  const {
    apiBase,
    projects,
    contextProjectId,
    globalSearchInput,
    labelClass,
    inputClass,
    buttonClass,
    primaryButtonClass,
    onSetContextProjectId,
    onSetGlobalSearchInput,
    onChangeTab,
    onRefreshAll
  } = props;

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <div className="min-w-[220px] flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">Multiagents Control Panel</h1>
          <p className="mt-1 text-xs text-slate-500">API: {apiBase}</p>
        </div>
        <label className="min-w-[200px]">
          <span className={labelClass}>Project context</span>
          <select
            className={inputClass}
            value={contextProjectId ?? ""}
            onChange={(event) => {
              if (event.target.value === "") {
                onSetContextProjectId(null);
                return;
              }
              const parsed = Number(event.target.value);
              onSetContextProjectId(Number.isNaN(parsed) ? null : parsed);
            }}
          >
            <option value="">all projects</option>
            {projects.map((project) => (
              <option key={project.id} value={String(project.id)}>
                {project.id}: {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-[220px] flex-1">
          <span className={labelClass}>Global search</span>
          <input
            className={inputClass}
            value={globalSearchInput}
            onChange={(event) => onSetGlobalSearchInput(event.target.value)}
            placeholder="runs/tasks/workflows"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={buttonClass} onClick={() => onChangeTab("runs")}>
            New run
          </button>
          <button type="button" className={buttonClass} onClick={() => onChangeTab("tasks")}>
            New task
          </button>
          <button type="button" className={buttonClass} onClick={() => onChangeTab("approvals")}>
            Approvals
          </button>
          <button type="button" className={primaryButtonClass} onClick={onRefreshAll}>
            Refresh all
          </button>
        </div>
      </div>
    </header>
  );
}
