import test from "node:test";
import assert from "node:assert/strict";
import {
  parseWorkflowStepsJson,
  validateWorkflowStepDrafts,
  workflowDraftsToSteps,
  workflowStepsToDrafts
} from "../../.test-dist/workflowEditorUtils.js";

test("parseWorkflowStepsJson validates top-level structure", () => {
  const notArray = parseWorkflowStepsJson('{"step_id":"a"}');
  assert.equal(notArray.steps, null);
  assert.equal(notArray.error, "Steps JSON must be an array.");

  const invalidEntry = parseWorkflowStepsJson('[1]');
  assert.equal(invalidEntry.steps, null);
  assert.equal(invalidEntry.error, "Step 1 must be an object.");
});

test("workflowStepsToDrafts and workflowDraftsToSteps preserve extra fields", () => {
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
  assert.equal(parsed.error, null);
  assert.ok(parsed.steps);

  const drafts = workflowStepsToDrafts(parsed.steps ?? []);
  assert.equal(drafts.length, 1);
  assert.equal(drafts[0].step_id, "plan");
  assert.equal(drafts[0].role_id, 2);
  assert.equal(drafts[0].prompt, "Plan");
  assert.deepEqual(drafts[0].depends_on, []);

  drafts[0].prompt = "Updated plan";
  const steps = workflowDraftsToSteps(drafts);
  assert.equal(steps.length, 1);
  assert.equal(steps[0].title, "Updated plan");
  assert.deepEqual(steps[0].required_artifacts, [{ artifact_type: "text" }]);
});

test("validateWorkflowStepDrafts catches duplicate ids and missing fields", () => {
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

  assert.equal(validation.hasErrors, true);
  assert.match(validation.stepErrorsByClientId.a.role_id ?? "", /Role is required/);
  assert.match(validation.stepErrorsByClientId.a.prompt ?? "", /Prompt is required/);
  assert.match(validation.stepErrorsByClientId.a.step_id ?? "", /Duplicate step id/);
  assert.match(validation.stepErrorsByClientId.b.step_id ?? "", /Duplicate step id/);
});

test("validateWorkflowStepDrafts catches unknown dependencies and cycles", () => {
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
  assert.equal(unknownDependency.hasErrors, true);
  assert.match(unknownDependency.stepErrorsByClientId.a.depends_on ?? "", /Unknown dependency/);

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
  assert.equal(cycle.hasErrors, true);
  assert.equal(cycle.formErrors.length, 1);
  assert.match(cycle.formErrors[0], /Dependency cycle detected/);
});
