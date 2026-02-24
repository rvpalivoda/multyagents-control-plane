# Task 014: Build skill pack for autonomous multi-agent delivery

## Metadata

- Status: `done`
- Priority: `P1`
- Owner: `codex`
- Created: `2026-02-23`
- Updated: `2026-02-23`

## Objective

Create a complete, validated set of project skills that guides implementation across architecture, backend, workflows, runner, UI, git/workspace, telegram, contracts, docker, and testing.

## Non-goals

- Implement runtime platform code.
- Install skills globally into `$CODEX_HOME/skills`.

## References

- Product spec: `docs/PRODUCT_SPEC.md#3-core-capabilities`
- Architecture: `docs/ARCHITECTURE.md#1-high-level-design`
- Plan phase: `docs/IMPLEMENTATION_PLAN.md#phase-0-foundation-2-3-days`

## Scope

- Create dedicated skill directories under `skills/`.
- Fill `SKILL.md` content with project-specific workflows.
- Add focused reference files per skill.
- Generate `agents/openai.yaml` metadata including `default_prompt`.
- Validate each skill with `quick_validate.py`.

## Acceptance criteria

- [x] At least one skill exists for each major implementation domain.
- [x] Each skill has non-placeholder `SKILL.md` frontmatter and body.
- [x] Each skill has `agents/openai.yaml`.
- [x] Each skill validates successfully with `quick_validate.py`.

## Implementation notes

Created 11 skills using `skill-creator` initializer, then replaced templates with concise domain workflows and references. Added default prompts for explicit invocation and validated all skill folders.

## Test plan

- [x] Run `quick_validate.py` across all skill directories.
- [x] Check directory structure and metadata files.

## Risks and mitigations

- Risk: skills may overlap and trigger ambiguously.
- Mitigation: keep descriptions explicit with clear usage contexts.

## Result

Created and validated:
- `skills/task-governance`
- `skills/architecture-guard`
- `skills/api-orchestrator-fastapi`
- `skills/workflow-dag-engine`
- `skills/host-runner-codex-cli`
- `skills/project-workspace-git`
- `skills/react-control-panel`
- `skills/telegram-human-loop`
- `skills/docker-local-stack`
- `skills/events-artifacts-contract`
- `skills/testing-observability`
