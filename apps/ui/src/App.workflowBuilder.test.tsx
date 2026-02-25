import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const DEFAULT_GET_PAYLOADS: Record<string, unknown> = {
  "/roles": [
    {
      id: 1,
      name: "coder",
      context7_enabled: true,
      system_prompt: "",
      allowed_tools: [],
      skill_packs: [],
      execution_constraints: {}
    }
  ],
  "/skill-packs": [],
  "/workflow-templates": [],
  "/projects": [],
  "/workflow-runs": [],
  "/tasks": []
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json"
    }
  });
}

function createWorkflowRunStub(id: number, overrides: Record<string, unknown> = {}) {
  return {
    id,
    workflow_template_id: null,
    task_ids: [],
    status: "created",
    initiated_by: null,
    created_at: "2026-02-25T00:00:00Z",
    updated_at: "2026-02-25T00:00:00Z",
    failure_categories: [],
    failure_triage_hints: [],
    suggested_next_actions: [],
    duration_ms: null,
    success_rate: 0,
    retries_total: 0,
    per_role: [],
    ...overrides
  };
}

function installFetchMock(overrides: Record<string, unknown> = {}) {
  const getPayloads = { ...DEFAULT_GET_PAYLOADS, ...overrides };
  let workflowTemplates = Array.isArray(getPayloads["/workflow-templates"])
    ? [...(getPayloads["/workflow-templates"] as unknown[])]
    : [];
  let workflowRuns = Array.isArray(getPayloads["/workflow-runs"])
    ? (getPayloads["/workflow-runs"] as unknown[]).map((item, index) =>
        createWorkflowRunStub(index + 1, item as Record<string, unknown>)
      )
    : [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const method = (init?.method ?? "GET").toUpperCase();
    const requestUrl =
      typeof input === "string" || input instanceof URL ? input.toString() : input.url;
    const url = new URL(requestUrl, "http://localhost");
    const path = url.pathname;

    if (method === "GET") {
      if (path === "/events") {
        return jsonResponse([]);
      }
      if (path === "/workflow-templates") {
        return jsonResponse(workflowTemplates);
      }
      if (path === "/workflow-runs") {
        return jsonResponse(workflowRuns);
      }
      if (path in getPayloads) {
        return jsonResponse(getPayloads[path]);
      }
    }

    if (method === "POST") {
      if (path === "/workflow-templates") {
        const payload = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
        const created = {
          id: workflowTemplates.length + 1,
          name: typeof payload.name === "string" ? payload.name : "workflow",
          project_id: payload.project_id ?? null,
          steps: Array.isArray(payload.steps) ? payload.steps : []
        };
        workflowTemplates = [created, ...workflowTemplates];
        return jsonResponse(created);
      }
      if (path === "/workflow-runs") {
        const payload = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
        const created = createWorkflowRunStub(workflowRuns.length + 1, {
          workflow_template_id: payload.workflow_template_id ?? null,
          task_ids: Array.isArray(payload.task_ids) ? payload.task_ids : [],
          initiated_by: typeof payload.initiated_by === "string" ? payload.initiated_by : null,
          updated_at: "2026-02-25T00:00:00Z"
        });
        workflowRuns = [created, ...workflowRuns];
        return jsonResponse(created);
      }
    }

    return jsonResponse({ detail: `Unhandled request: ${method} ${path}` }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function openWorkflowsTab() {
  const user = userEvent.setup();
  const workflowTabButtons = await screen.findAllByRole("button", { name: "Workflows" });
  await user.click(workflowTabButtons[0]);
  await screen.findByRole("heading", { name: "Workflow Templates" });
  return user;
}

describe("workflow builder critical flows", () => {
  beforeEach(() => {
    installFetchMock();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("supports quick-create step editing and syncs updates to raw JSON", async () => {
    render(<App />);
    const user = await openWorkflowsTab();
    await screen.findAllByRole("option", { name: /1:\s*coder/i });

    await user.click(screen.getByRole("button", { name: "Add step" }));

    const stepIdInputs = screen.getAllByLabelText("Step id");
    const promptInputs = screen.getAllByLabelText("Prompt");
    const roleSelects = screen.getAllByLabelText("Role");
    const targetStep = stepIdInputs[stepIdInputs.length - 1] as HTMLInputElement;
    const targetPrompt = promptInputs[promptInputs.length - 1] as HTMLTextAreaElement;
    const targetRole = roleSelects[roleSelects.length - 1] as HTMLSelectElement;

    await user.clear(targetStep);
    await user.type(targetStep, "review");
    await user.selectOptions(targetRole, "1");
    fireEvent.change(targetPrompt, { target: { value: "" } });
    await user.type(targetPrompt, "Review generated output");

    await user.click(screen.getByRole("button", { name: "Raw JSON" }));
    const stepsJson = screen.getByLabelText("Steps JSON") as HTMLTextAreaElement;

    expect(stepsJson.value).toContain('"step_id": "review"');
    expect(stepsJson.value).toContain('"title": "Review generated output"');
  });

  it("shows quick-create validation errors and blocks workflow submit", async () => {
    render(<App />);
    const user = await openWorkflowsTab();

    const stepIdInputs = screen.getAllByLabelText("Step id");
    await user.clear(stepIdInputs[1]);
    await user.type(stepIdInputs[1], "plan");

    const duplicateErrors = await screen.findAllByText("Duplicate step id 'plan'.");
    expect(duplicateErrors.length).toBeGreaterThan(0);

    const promptInputs = screen.getAllByLabelText("Prompt");
    fireEvent.change(promptInputs[1], { target: { value: "" } });
    const promptErrors = await screen.findAllByText("Prompt is required.");
    expect(promptErrors.length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Create" })).toBeDisabled();
  });

  it("syncs valid raw JSON changes back into quick-create fields", async () => {
    render(<App />);
    const user = await openWorkflowsTab();

    await user.click(screen.getByRole("button", { name: "Raw JSON" }));
    const stepsJson = screen.getByLabelText("Steps JSON");
    fireEvent.change(stepsJson, {
      target: {
        value: JSON.stringify(
          [
            {
              step_id: "analysis",
              role_id: 1,
              title: "Analyze request",
              depends_on: []
            }
          ],
          null,
          2
        )
      }
    });

    await user.click(screen.getByRole("button", { name: "Quick create" }));
    await waitFor(() => {
      expect(screen.getAllByLabelText("Step id")).toHaveLength(1);
    });

    const stepId = screen.getByLabelText("Step id") as HTMLInputElement;
    const prompt = screen.getByLabelText("Prompt") as HTMLTextAreaElement;
    expect(stepId.value).toBe("analysis");
    expect(prompt.value).toBe("Analyze request");
  });

  it("keeps raw JSON mode active when JSON is invalid during mode switch", async () => {
    render(<App />);
    const user = await openWorkflowsTab();

    await user.click(screen.getByRole("button", { name: "Raw JSON" }));
    fireEvent.change(screen.getByLabelText("Steps JSON"), {
      target: { value: "{" }
    });

    await user.click(screen.getByRole("button", { name: "Quick create" }));

    expect(
      await screen.findByText(/Steps JSON must be valid before switching to Quick create\./)
    ).toBeVisible();
    expect(screen.getByDisplayValue("{")).toBeVisible();
  });

  it("applies developer workflow presets in quick create", async () => {
    render(<App />);
    const user = await openWorkflowsTab();

    const presetCases = [
      {
        id: "feature-delivery",
        scenario: "Plan, implement, test, and review a product increment with explicit quality gates.",
        workflowName: "feature-delivery",
        stepIds: ["plan", "implement", "test", "review"]
      },
      {
        id: "bugfix-fast-lane",
        scenario: "Triage, patch, and verify urgent defects with a short delivery path.",
        workflowName: "bugfix-fast-lane",
        stepIds: ["triage", "fix", "verify"]
      },
      {
        id: "release-prep-lane",
        scenario: "Harden build, verify rollout readiness, and capture release evidence before go-live.",
        workflowName: "release-prep-lane",
        stepIds: ["freeze", "regression", "notes", "go-no-go"]
      },
      {
        id: "incident-hotfix-lane",
        scenario: "Contain production impact, ship a hotfix, and record follow-up actions quickly.",
        workflowName: "incident-hotfix-lane",
        stepIds: ["stabilize", "patch", "validate", "follow-up"]
      }
    ];

    const workflowNameInput = screen.getByLabelText("Name") as HTMLInputElement;
    const presetSelect = screen.getByLabelText("Preset");
    for (const presetCase of presetCases) {
      await user.selectOptions(presetSelect, presetCase.id);
      expect(screen.getByText(presetCase.scenario)).toBeVisible();
      await user.click(screen.getByRole("button", { name: "Apply preset" }));

      expect(workflowNameInput.value).toBe(presetCase.workflowName);
      const stepIds = (screen.getAllByLabelText("Step id") as HTMLInputElement[]).map((input) => input.value);
      expect(stepIds).toEqual(presetCase.stepIds);
    }
  });

  it("applies article/social/localization presets in quick create", async () => {
    render(<App />);
    const user = await openWorkflowsTab();

    const presetCases = [
      {
        id: "article-pipeline",
        scenario: "Produce a long-form article from research through editorial and fact-check gates.",
        workflowName: "article-pipeline",
        stepIds: ["research", "outline", "draft", "edit", "fact-check", "final"]
      },
      {
        id: "social-pipeline",
        scenario: "Generate social content variants with hook iteration and QA before final delivery.",
        workflowName: "social-pipeline",
        stepIds: ["ideas", "hooks", "variants", "qa", "final"]
      },
      {
        id: "localization-pipeline",
        scenario: "Adapt source text for a target locale with tone QA and final sign-off.",
        workflowName: "localization-pipeline",
        stepIds: ["source", "adapt", "tone-qa", "final"]
      }
    ];

    const workflowNameInput = screen.getByLabelText("Name") as HTMLInputElement;
    const presetSelect = screen.getByLabelText("Preset");
    for (const presetCase of presetCases) {
      await user.selectOptions(presetSelect, presetCase.id);
      expect(screen.getByText(presetCase.scenario)).toBeVisible();
      await user.click(screen.getByRole("button", { name: "Apply preset" }));

      expect(workflowNameInput.value).toBe(presetCase.workflowName);
      const stepIds = (screen.getAllByLabelText("Step id") as HTMLInputElement[]).map((input) => input.value);
      expect(stepIds).toEqual(presetCase.stepIds);
    }
  });

  it("creates and quick launches article preset without raw JSON editing", async () => {
    const fetchMock = installFetchMock();
    render(<App />);
    const user = await openWorkflowsTab();

    await user.selectOptions(screen.getByLabelText("Preset"), "article-pipeline");
    await user.click(screen.getByRole("button", { name: "Apply preset" }));
    expect(screen.queryByLabelText("Steps JSON")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      const workflowCreateCall = fetchMock.mock.calls.find(([request, requestInit]) => {
        const requestUrl =
          typeof request === "string" || request instanceof URL ? request.toString() : request.url;
        const url = new URL(requestUrl, "http://localhost");
        const method = (requestInit?.method ?? "GET").toUpperCase();
        return method === "POST" && url.pathname === "/workflow-templates";
      });
      expect(workflowCreateCall).toBeDefined();

      const createPayload = JSON.parse(String((workflowCreateCall?.[1] as RequestInit).body)) as {
        name: string;
        steps: Array<{ step_id: string }>;
      };
      expect(createPayload.name).toBe("article-pipeline");
      expect(createPayload.steps.map((step) => step.step_id)).toEqual([
        "research",
        "outline",
        "draft",
        "edit",
        "fact-check",
        "final"
      ]);
    });

    await user.click(screen.getByRole("button", { name: "Launch run" }));

    await waitFor(() => {
      const runCreateCall = fetchMock.mock.calls.find(([request, requestInit]) => {
        const requestUrl =
          typeof request === "string" || request instanceof URL ? request.toString() : request.url;
        const url = new URL(requestUrl, "http://localhost");
        const method = (requestInit?.method ?? "GET").toUpperCase();
        return method === "POST" && url.pathname === "/workflow-runs";
      });
      expect(runCreateCall).toBeDefined();
      const payload = JSON.parse(String((runCreateCall?.[1] as RequestInit).body));
      expect(payload).toEqual({
        workflow_template_id: 1,
        task_ids: [],
        initiated_by: "ui-workflow-quick-launch"
      });
    });
  });

  it("quick launches a run from workflows tab with minimal fields", async () => {
    const fetchMock = installFetchMock({
      "/workflow-templates": [
        {
          id: 7,
          name: "feature-delivery",
          project_id: null,
          steps: [
            { step_id: "plan", role_id: 1, title: "Plan", depends_on: [] },
            { step_id: "build", role_id: 1, title: "Build", depends_on: ["plan"] }
          ]
        }
      ]
    });

    render(<App />);
    const user = await openWorkflowsTab();

    await user.click(screen.getByText("feature-delivery"));
    await user.click(screen.getByRole("button", { name: "Launch run" }));

    await waitFor(() => {
      const runCreateCall = fetchMock.mock.calls.find(([request, requestInit]) => {
        const requestUrl =
          typeof request === "string" || request instanceof URL ? request.toString() : request.url;
        const url = new URL(requestUrl, "http://localhost");
        const method = (requestInit?.method ?? "GET").toUpperCase();
        return method === "POST" && url.pathname === "/workflow-runs";
      });
      expect(runCreateCall).toBeDefined();
      const payload = JSON.parse(String((runCreateCall?.[1] as RequestInit).body));
      expect(payload).toEqual({
        workflow_template_id: 7,
        task_ids: [],
        initiated_by: "ui-workflow-quick-launch"
      });
    });
  });

  it("validates quick launch template ID before dispatch", async () => {
    const fetchMock = installFetchMock();
    render(<App />);
    const user = await openWorkflowsTab();

    const templateIdInput = screen.getByLabelText("Template ID");
    const launchButton = screen.getByRole("button", { name: "Launch run" });
    expect(launchButton).toBeDisabled();

    await user.type(templateIdInput, "invalid");
    expect(await screen.findByText("Template ID must be a number.")).toBeVisible();
    expect(launchButton).toBeDisabled();

    const runCreateCalls = fetchMock.mock.calls.filter(([request, requestInit]) => {
      const requestUrl =
        typeof request === "string" || request instanceof URL ? request.toString() : request.url;
      const url = new URL(requestUrl, "http://localhost");
      const method = (requestInit?.method ?? "GET").toUpperCase();
      return method === "POST" && url.pathname === "/workflow-runs";
    });
    expect(runCreateCalls).toHaveLength(0);
  });

  it("quick launches using manual template ID when no row is selected", async () => {
    const fetchMock = installFetchMock();
    render(<App />);
    const user = await openWorkflowsTab();

    await user.type(screen.getByLabelText("Template ID"), "42");
    await user.clear(screen.getByLabelText("Initiated by"));
    await user.type(screen.getByLabelText("Initiated by"), "manual-launch");
    await user.click(screen.getByRole("button", { name: "Launch run" }));

    await waitFor(() => {
      const runCreateCall = fetchMock.mock.calls.find(([request, requestInit]) => {
        const requestUrl =
          typeof request === "string" || request instanceof URL ? request.toString() : request.url;
        const url = new URL(requestUrl, "http://localhost");
        const method = (requestInit?.method ?? "GET").toUpperCase();
        return method === "POST" && url.pathname === "/workflow-runs";
      });
      expect(runCreateCall).toBeDefined();
      const payload = JSON.parse(String((runCreateCall?.[1] as RequestInit).body));
      expect(payload).toEqual({
        workflow_template_id: 42,
        task_ids: [],
        initiated_by: "manual-launch"
      });
    });
  });
});
