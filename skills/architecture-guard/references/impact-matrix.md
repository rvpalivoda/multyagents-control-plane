# Architecture Impact Matrix

## Low impact

- Internal refactor without API/schema changes
- UI-only layout changes

## Medium impact

- New endpoint compatible with existing contracts
- Additional event type preserving old consumers

## High impact

- Breaking schema change
- Workflow state machine transition changes
- Runner protocol changes
- Deployment topology changes

For high impact changes: create ADR and migration strategy.
