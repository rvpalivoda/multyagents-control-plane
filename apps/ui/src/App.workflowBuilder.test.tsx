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

function installFetchMock(overrides: Record<string, unknown> = {}) {
  const getPayloads = { ...DEFAULT_GET_PAYLOADS, ...overrides };

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
      if (path in getPayloads) {
        return jsonResponse(getPayloads[path]);
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
});
