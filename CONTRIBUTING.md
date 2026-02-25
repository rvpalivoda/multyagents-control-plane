# Contributing Guide

## Workflow

1. Create branch from `master` (or `develop` when introduced): `feature/<task-id>-short-name`.
2. Link task in `docs/tasks/TASK-xxx.md`.
3. Keep changes scoped and atomic.
4. Run local checks before PR.
5. Open PR using template and request review.

## Commit format

Use conventional style:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `refactor: ...`
- `test: ...`
- `chore: ...`

Include task when relevant, e.g. `feat(task-052): add failure triage hints`.

## Local validation

### API
```bash
cd apps/api
pip install -e .[dev]
pytest -q
```

### Telegram bot
```bash
cd apps/telegram-bot
pip install -e .[dev]
pytest -q
```

### UI
```bash
cd apps/ui
npm ci
npm test
npm run build
```

## Security

- Never commit secrets, tokens, local env files.
- Use least-privilege execution constraints.
- Document high-risk changes in PR risk section.
