import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { TaskRead, WorkflowRunRead } from "../../../../packages/contracts/ts/context7";
import { RunsCenterSection } from "./RunsCenterSection";

function buildRun(): WorkflowRunRead {
  return {
    id: 101,
    workflow_template_id: 7,
    task_ids: [201],
    status: "running",
    initiated_by: "ui-test",
    created_at: "2026-02-25T10:00:00Z",
    updated_at: "2026-02-25T10:01:00Z",
    failure_categories: [],
    failure_triage_hints: [],
    suggested_next_actions: [],
    duration_ms: 1000,
    success_rate: 50,
    retries_total: 1,
    per_role: [],
    quality_gate_summary: {
      status: "pending",
      summary_text: "1/2 task(s) currently pass; 1 task(s) still pending quality checks.",
      total_tasks: 2,
      passing_tasks: 1,
      failing_tasks: 0,
      pending_tasks: 1,
      not_configured_tasks: 0,
      total_checks: 3,
      passed_checks: 2,
      failed_checks: 0,
      pending_checks: 1,
      skipped_checks: 0,
      blocker_failures: 0,
      warning_failures: 0
    }
  };
}

function buildTask(): TaskRead {
  return {
    id: 201,
    role_id: 1,
    title: "Draft",
    context7_mode: "inherit",
    execution_mode: "no-workspace",
    status: "queued",
    requires_approval: false,
    project_id: null,
    lock_paths: [],
    runner_message: "queued",
    started_at: null,
    finished_at: null,
    exit_code: null,
    failure_category: null,
    failure_triage_hints: [],
    suggested_next_actions: [],
    quality_gate_summary: {
      status: "pending",
      summary_text: "0/1 checks passed, 1 pending.",
      total_checks: 1,
      passed_checks: 0,
      failed_checks: 0,
      pending_checks: 1,
      skipped_checks: 0,
      blocker_failures: 0,
      warning_failures: 0,
      checks: []
    }
  };
}

describe("RunsCenterSection quality gate rendering", () => {
  it("renders run and task quality gate summaries", () => {
    const run = buildRun();
    const task = buildTask();
    render(
      <RunsCenterSection
        sectionClass="section"
        labelClass="label"
        inputClass="input"
        buttonClass="button"
        primaryButtonClass="primary"
        tableClass="table"
        thClass="th"
        tdClass="td"
        runWorkflowTemplateIdInput=""
        runTaskIdsInput=""
        runInitiatedBy=""
        runSearchInput=""
        selectedRunId={run.id}
        filteredRuns={[run]}
        roleNameById={{}}
        workflowNameById={{}}
        workflowProjectIdById={{}}
        projectNameById={{}}
        selectedRun={run}
        selectedRunTasks={[task]}
        runDispatchResult={null}
        runPartialRerunResult={null}
        timelineEvents={[]}
        onRunWorkflowTemplateIdChange={vi.fn()}
        onRunTaskIdsChange={vi.fn()}
        onRunInitiatedByChange={vi.fn()}
        onRunSearchChange={vi.fn()}
        onCreateWorkflowRun={vi.fn()}
        onRefreshRuns={vi.fn()}
        onRefreshTimeline={vi.fn()}
        onRunAction={vi.fn()}
        onDispatchReadyTask={vi.fn()}
        onPartialRerun={vi.fn()}
        onSelectRun={vi.fn()}
      />
    );

    expect(screen.getAllByText(/Quality gates: pending/).length).toBeGreaterThan(0);
    expect(screen.getByText("1/2 task(s) currently pass; 1 task(s) still pending quality checks.")).toBeVisible();
    expect(screen.getByText("0/1 checks passed, 1 pending.")).toBeVisible();
  });

  it("submits partial rerun payload for selected failed task", async () => {
    const run = buildRun();
    const failedTask: TaskRead = {
      ...buildTask(),
      id: 301,
      title: "Retry me",
      status: "failed",
      runner_message: "failed"
    };
    const onPartialRerun = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    render(
      <RunsCenterSection
        sectionClass="section"
        labelClass="label"
        inputClass="input"
        buttonClass="button"
        primaryButtonClass="primary"
        tableClass="table"
        thClass="th"
        tdClass="td"
        runWorkflowTemplateIdInput=""
        runTaskIdsInput=""
        runInitiatedBy=""
        runSearchInput=""
        selectedRunId={run.id}
        filteredRuns={[run]}
        roleNameById={{}}
        workflowNameById={{}}
        workflowProjectIdById={{}}
        projectNameById={{}}
        selectedRun={run}
        selectedRunTasks={[failedTask]}
        runDispatchResult={null}
        runPartialRerunResult={null}
        timelineEvents={[]}
        onRunWorkflowTemplateIdChange={vi.fn()}
        onRunTaskIdsChange={vi.fn()}
        onRunInitiatedByChange={vi.fn()}
        onRunSearchChange={vi.fn()}
        onCreateWorkflowRun={vi.fn()}
        onRefreshRuns={vi.fn()}
        onRefreshTimeline={vi.fn()}
        onRunAction={vi.fn()}
        onDispatchReadyTask={vi.fn()}
        onPartialRerun={onPartialRerun}
        onSelectRun={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText("Reason"), "retry after fix");
    await user.click(screen.getByRole("button", { name: "Rerun selected failed branches" }));

    expect(confirmSpy).toHaveBeenCalledOnce();
    expect(onPartialRerun).toHaveBeenCalledWith({
      task_ids: [failedTask.id],
      step_ids: [],
      requested_by: "ui-operator",
      reason: "retry after fix",
      auto_dispatch: true,
      max_dispatch: 10
    });
    confirmSpy.mockRestore();
  });
});
