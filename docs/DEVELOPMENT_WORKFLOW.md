# Development Workflow (Best Practices)

## Branch strategy

- `master` — stable trunk
- `feature/*` — short-lived feature branches
- `fix/*` — urgent fixes

## PR policy

- Minimum 1 review before merge
- CI must be green
- Squash merge preferred for clean history

## Task governance

- Every substantial change maps to `docs/tasks/TASK-xxx.md`
- Update task status and evidence in same PR

## Release hygiene

- Tag milestone commits (`v0.x.y`)
- Keep changelog entries per feature/fix cluster

## Troubleshooting

- Local gateway/sandbox failures: 
