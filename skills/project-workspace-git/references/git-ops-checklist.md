# Git Operations Checklist

## Shared mode

- Validate allowed write paths
- Acquire soft lock leases by path glob
- Release locks on success/failure/timeout

## Isolated mode

- Create branch `run/<run-id>/task/<task-id>`
- Create worktree under managed temp root
- Run checks before integration
- Remove worktree after completion

## Integration gate

- Reviewer task completed
- Required checks passed
- Conflict status resolved
