import { describe, expect, it } from "vitest";

import {
  parseWorkflowStepsJson,
  validateWorkflowStepDrafts,
  workflowDraftsToSteps,
  workflowStepsToDrafts
} from "./workflowEditorUtils";

describe("workflowEditorUtils", () => {
  it("parseWorkflowStepsJson validates top-level structure", () => {
    const notArray = parseWorkflowStepsJson('{"step_id":"a"}');
    expect(notArray.steps).toBeNull();
    expect(notArray.error).toBe("Steps JSON must be an array.");

    const invalidEntry = parseWorkflowStepsJson("[1]");
    expect(invalidEntry.steps).toBeNull();
    expect(invalidEntry.error).toBe("Step 1 must be an object.");
  });

  it("workflowStepsToDrafts and workflowDraftsToSteps preserve extra fields", () => {
    const parsed = parseWorkflowStepsJson(
      JSON.stringify([
        {
          step_id: "plan",
          role_id: 2,
          title: "Plan",
          depends_on: [],
          required_artifacts: [{ artifact_type: "text" }]
        }
      ])
    );
    expect(parsed.error).toBeNull();
    expect(parsed.steps).toBeTruthy();

    const drafts = workflowStepsToDrafts(parsed.steps ?? []);
    expect(drafts).toHaveLength(1);
    expect(drafts[0].step_id).toBe("plan");
    expect(drafts[0].role_id).toBe(2);
    expect(drafts[0].prompt).toBe("Plan");
    expect(drafts[0].depends_on).toEqual([]);

    drafts[0].prompt = "Updated plan";
    const steps = workflowDraftsToSteps(drafts);
    expect(steps).toHaveLength(1);
    expect(steps[0].title).toBe("Updated plan");
    expect(steps[0].required_artifacts).toEqual([{ artifact_type: "text" }]);
  });

  it("validateWorkflowStepDrafts catches duplicate ids and missing fields", () => {
    const validation = validateWorkflowStepDrafts([
      {
        client_id: "a",
        step_id: "dup",
        role_id: null,
        prompt: "",
        depends_on: [],
        raw: {}
      },
      {
        client_id: "b",
        step_id: "dup",
        role_id: 1,
        prompt: "Build",
        depends_on: [],
        raw: {}
      }
    ]);

    expect(validation.hasErrors).toBe(true);
    expect(validation.stepErrorsByClientId.a.role_id).toMatch(/Role is required/);
    expect(validation.stepErrorsByClientId.a.prompt).toMatch(/Prompt is required/);
    expect(validation.stepErrorsByClientId.a.step_id).toMatch(/Duplicate step id/);
    expect(validation.stepErrorsByClientId.b.step_id).toMatch(/Duplicate step id/);
  });

  it("validateWorkflowStepDrafts catches unknown dependencies and cycles", () => {
    const unknownDependency = validateWorkflowStepDrafts([
      {
        client_id: "a",
        step_id: "plan",
        role_id: 1,
        prompt: "Plan",
        depends_on: ["missing"],
        raw: {}
      }
    ]);
    expect(unknownDependency.hasErrors).toBe(true);
    expect(unknownDependency.stepErrorsByClientId.a.depends_on).toMatch(/Unknown dependency/);

    const cycle = validateWorkflowStepDrafts([
      {
        client_id: "a",
        step_id: "plan",
        role_id: 1,
        prompt: "Plan",
        depends_on: ["build"],
        raw: {}
      },
      {
        client_id: "b",
        step_id: "build",
        role_id: 1,
        prompt: "Build",
        depends_on: ["plan"],
        raw: {}
      }
    ]);
    expect(cycle.hasErrors).toBe(true);
    expect(cycle.formErrors).toHaveLength(1);
    expect(cycle.formErrors[0]).toMatch(/Dependency cycle detected/);
  });
});
