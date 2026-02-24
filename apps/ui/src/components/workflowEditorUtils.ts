export type WorkflowStepRecord = Record<string, unknown>;

export type WorkflowStepDraft = {
  client_id: string;
  step_id: string;
  role_id: number | null;
  prompt: string;
  depends_on: string[];
  raw: WorkflowStepRecord;
};

export type WorkflowStepDraftFieldErrors = {
  step_id?: string;
  role_id?: string;
  prompt?: string;
  depends_on?: string;
};

export type WorkflowStepDraftValidation = {
  hasErrors: boolean;
  formErrors: string[];
  stepErrorsByClientId: Record<string, WorkflowStepDraftFieldErrors>;
};

export type WorkflowStepsJsonParseResult = {
  steps: WorkflowStepRecord[] | null;
  error: string | null;
};

let workflowDraftCounter = 0;

function nextWorkflowDraftId(): string {
  workflowDraftCounter += 1;
  return `workflow-step-${workflowDraftCounter}`;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const values: string[] = [];
  value.forEach((item) => {
    if (typeof item === "string") {
      const trimmed = item.trim();
      if (trimmed.length > 0 && !values.includes(trimmed)) {
        values.push(trimmed);
      }
    }
  });
  return values;
}

function appendStepError(
  errors: Record<string, WorkflowStepDraftFieldErrors>,
  clientId: string,
  field: keyof WorkflowStepDraftFieldErrors,
  message: string
) {
  const current = errors[clientId] ?? {};
  if (current[field]) {
    current[field] = `${current[field]}; ${message}`;
  } else {
    current[field] = message;
  }
  errors[clientId] = current;
}

export function createWorkflowStepDraft(defaultRoleId: number | null, index: number): WorkflowStepDraft {
  return {
    client_id: nextWorkflowDraftId(),
    step_id: `step-${index + 1}`,
    role_id: defaultRoleId,
    prompt: "",
    depends_on: [],
    raw: {}
  };
}

export function parseWorkflowStepsJson(value: string): WorkflowStepsJsonParseResult {
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!Array.isArray(parsed)) {
      return { steps: null, error: "Steps JSON must be an array." };
    }

    const steps: WorkflowStepRecord[] = [];
    for (let index = 0; index < parsed.length; index += 1) {
      const item = parsed[index];
      if (!item || typeof item !== "object" || Array.isArray(item)) {
        return { steps: null, error: `Step ${index + 1} must be an object.` };
      }
      steps.push({ ...(item as WorkflowStepRecord) });
    }
    return { steps, error: null };
  } catch {
    return { steps: null, error: "Steps JSON is not valid JSON." };
  }
}

export function workflowStepsToDrafts(steps: WorkflowStepRecord[]): WorkflowStepDraft[] {
  return steps.map((step, index) => {
    const stepIdValue = step.step_id;
    const roleIdValue = step.role_id;
    const promptValue = step.title;
    const dependsOnValue = step.depends_on;

    return {
      client_id: nextWorkflowDraftId(),
      step_id: typeof stepIdValue === "string" ? stepIdValue : `step-${index + 1}`,
      role_id: typeof roleIdValue === "number" && Number.isFinite(roleIdValue) ? roleIdValue : null,
      prompt: typeof promptValue === "string" ? promptValue : "",
      depends_on: toStringArray(dependsOnValue),
      raw: { ...step }
    };
  });
}

export function workflowDraftsToSteps(drafts: WorkflowStepDraft[]): WorkflowStepRecord[] {
  return drafts.map((draft) => {
    const dependsOn = toStringArray(draft.depends_on);
    return {
      ...draft.raw,
      step_id: draft.step_id,
      role_id: draft.role_id,
      title: draft.prompt,
      depends_on: dependsOn
    };
  });
}

function detectCycle(nodes: string[], dependenciesByNode: Record<string, string[]>): string[] | null {
  const visitState: Record<string, 0 | 1 | 2> = {};
  const stack: string[] = [];

  const walk = (node: string): string[] | null => {
    visitState[node] = 1;
    stack.push(node);

    const dependencies = dependenciesByNode[node] ?? [];
    for (const dependency of dependencies) {
      const state = visitState[dependency] ?? 0;
      if (state === 0) {
        const nested = walk(dependency);
        if (nested) {
          return nested;
        }
      } else if (state === 1) {
        const start = stack.indexOf(dependency);
        if (start >= 0) {
          return [...stack.slice(start), dependency];
        }
      }
    }

    stack.pop();
    visitState[node] = 2;
    return null;
  };

  for (const node of nodes) {
    if ((visitState[node] ?? 0) === 0) {
      const cycle = walk(node);
      if (cycle) {
        return cycle;
      }
    }
  }
  return null;
}

export function validateWorkflowStepDrafts(drafts: WorkflowStepDraft[]): WorkflowStepDraftValidation {
  const formErrors: string[] = [];
  const stepErrorsByClientId: Record<string, WorkflowStepDraftFieldErrors> = {};
  const stepIds = new Map<string, string[]>();

  drafts.forEach((draft) => {
    const stepId = draft.step_id.trim();
    if (stepId.length === 0) {
      appendStepError(stepErrorsByClientId, draft.client_id, "step_id", "Step id is required.");
    } else {
      const members = stepIds.get(stepId) ?? [];
      members.push(draft.client_id);
      stepIds.set(stepId, members);
    }

    if (draft.role_id === null || !Number.isFinite(draft.role_id)) {
      appendStepError(stepErrorsByClientId, draft.client_id, "role_id", "Role is required.");
    }

    if (draft.prompt.trim().length === 0) {
      appendStepError(stepErrorsByClientId, draft.client_id, "prompt", "Prompt is required.");
    }
  });

  stepIds.forEach((members, stepId) => {
    if (members.length > 1) {
      members.forEach((clientId) => {
        appendStepError(stepErrorsByClientId, clientId, "step_id", `Duplicate step id '${stepId}'.`);
      });
    }
  });

  const uniqueStepIds = new Set<string>([...stepIds.keys()]);
  const hasDuplicateIds = [...stepIds.values()].some((members) => members.length > 1);

  drafts.forEach((draft) => {
    const stepId = draft.step_id.trim();
    const dependencies = toStringArray(draft.depends_on);
    dependencies.forEach((dependency) => {
      if (stepId.length > 0 && dependency === stepId) {
        appendStepError(stepErrorsByClientId, draft.client_id, "depends_on", "Step cannot depend on itself.");
      } else if (!uniqueStepIds.has(dependency)) {
        appendStepError(
          stepErrorsByClientId,
          draft.client_id,
          "depends_on",
          `Unknown dependency '${dependency}'.`
        );
      }
    });
  });

  if (!hasDuplicateIds) {
    const ids = drafts
      .map((draft) => draft.step_id.trim())
      .filter((item) => item.length > 0);
    const dependenciesByNode: Record<string, string[]> = {};
    drafts.forEach((draft) => {
      const stepId = draft.step_id.trim();
      if (stepId.length === 0) {
        return;
      }
      dependenciesByNode[stepId] = toStringArray(draft.depends_on).filter((dependency) => uniqueStepIds.has(dependency));
    });

    const cycle = detectCycle(ids, dependenciesByNode);
    if (cycle) {
      formErrors.push(`Dependency cycle detected: ${cycle.join(" -> ")}`);
      const cycleIds = new Set<string>(cycle);
      drafts.forEach((draft) => {
        if (cycleIds.has(draft.step_id.trim())) {
          appendStepError(stepErrorsByClientId, draft.client_id, "depends_on", "Step is in a dependency cycle.");
        }
      });
    }
  }

  if (drafts.length === 0) {
    formErrors.push("At least one step is required.");
  }

  const hasErrors = formErrors.length > 0 || Object.keys(stepErrorsByClientId).length > 0;
  return { hasErrors, formErrors, stepErrorsByClientId };
}
