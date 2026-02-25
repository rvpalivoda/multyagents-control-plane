# Workflow Creation Guide (Operator UX)

This guide describes the current workflow creation UX in the control panel `Workflows` tab.

References:
- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#4-execution-lifecycle`

## 1. Before you start

- Create at least one role in the `Roles` tab first.
- Optional: create/select a project if you want workflow templates scoped to a project.

## 2. Quick create mode

Use `Quick create` when you want guided step cards and inline validation.

Steps:
1. Open `Workflows`.
2. Enter workflow `Name` and optional `Project ID`.
3. Keep mode on `Quick create`.
4. For each step card, fill:
   - `Step id`
   - `Role`
   - `Prompt`
   - `Depends on` (checkboxes from existing step IDs)
5. Use `Add step` to extend the DAG, `Remove` to delete a step.
6. Click `Create` (or `Update selected` for existing template).

Quick mode mapping:
- UI `Prompt` is written to API field `title`.
- Quick mode edits these fields directly: `step_id`, `role_id`, `title` (`Prompt`), `depends_on`.

## 3. Advanced JSON mode (`Raw JSON`)

Use `Raw JSON` when you need to edit payload directly.

Steps:
1. Switch mode to `Raw JSON`.
2. Edit `Steps JSON` as a JSON array of objects.
3. Click `Create` or `Update selected`.

Minimum valid step object:

```json
[
  {
    "step_id": "plan",
    "role_id": 1,
    "title": "Plan the implementation",
    "depends_on": []
  },
  {
    "step_id": "build",
    "role_id": 1,
    "title": "Implement and verify",
    "depends_on": ["plan"]
  }
]
```

Optional API field currently supported per step:
- `required_artifacts` (for artifact handoff constraints).

## 4. Switching between Quick and Raw JSON

- `Quick create` -> `Raw JSON`: always available; JSON is generated from current step cards.
- `Raw JSON` -> `Quick create`: allowed only when `Steps JSON` is valid JSON array of objects.
- If JSON is invalid, UI blocks switch back and shows:
  - `Steps JSON must be valid before switching to Quick create.`

## 5. Current validation behavior

Quick create validates before create/update:
- step list must not be empty (`At least one step is required.`)
- `Step id` is required and must be unique
- `Role` is required
- `Prompt` is required
- no self dependency
- dependency must reference known `step_id`
- no dependency cycles

Raw JSON mode validates in UI only:
- JSON syntax must be valid
- root value must be an array
- each step must be an object

Server-side API validations still apply for both modes:
- `steps` must contain at least one step
- DAG checks: unique IDs, known dependencies, no self dependency, no cycle
- `required_artifacts.from_step_id` must reference a dependency in `depends_on`
- each `role_id` must exist (otherwise `404`)
- `project_id` must exist when provided (otherwise `404`)

## 6. Best practices

- Keep `step_id` short and stable (`plan`, `build`, `review`).
- Use deterministic dependency chains; avoid unnecessary fan-in/fan-out.
- Prefer adding one step at a time and resolving inline errors immediately.
- Use `Raw JSON` only for advanced fields or bulk edits, then switch back to `Quick create` for sanity checks.
- Keep prompts outcome-focused and specific per step.
- Refresh workflows after major edits and re-select the template before running.

## 7. Mini pre-run checklist

Before creating a workflow run:

- [ ] Workflow template is saved (`Create`/`Update selected` succeeded).
- [ ] No validation errors are visible in `Workflows`.
- [ ] Every step has a real existing role.
- [ ] Dependencies form an acyclic DAG and reference existing step IDs only.
- [ ] If `Project ID` is set, it points to an existing project.
- [ ] In `Runs`, selected `workflow_template_id` matches the template you just edited.
