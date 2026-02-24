# Shared Contracts

This directory stores versioned API contracts shared across services.

## Versioning policy

- Contract files live under `v<major>/`.
- Breaking changes require a new major folder (`v2`, `v3`, ...).
- Additive non-breaking fields are allowed within the same major version.
- Consumers should pin the contract major version they support.

## Current contract

- `v1/context7.schema.json`
- TypeScript mirrors: `ts/context7.ts`
