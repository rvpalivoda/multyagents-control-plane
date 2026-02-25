# multyagents.dev

Local multi-agent control plane project.

## Repository structure

- `apps/api` - FastAPI orchestrator API
- `apps/ui` - React control panel
- `apps/telegram-bot` - Telegram channel service scaffold
- `apps/host-runner` - host-side runner scaffold for local codex CLI
- `infra/compose` - local Docker Compose stack
- `docs` - spec, architecture, plan, tasks, ADRs
- `skills` - project-specific Codex skills

## Documentation

- Main docs index: `docs/README.md`
- Local failure recovery runbooks:
  - `docs/runbooks/RUNNER_OFFLINE.md`
  - `docs/runbooks/STUCK_QUEUED_RUNNING.md`
  - `docs/runbooks/WORKTREE_CONFLICT_CLEANUP.md`

## Quick start

### One command launcher

```bash
./scripts/multyagents up
```

Useful commands:

```bash
./scripts/multyagents status
./scripts/multyagents logs
./scripts/multyagents down
./scripts/multyagents e2e
./scripts/multyagents desktop
```

`desktop` starts an Electron control panel (first run installs `apps/desktop` dependencies).

### API tests

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

### UI build

```bash
cd apps/ui
npm install
npm run build
```

### Compose stack

```bash
cd infra/compose
cp .env.example .env
docker compose up --build
```

Host runner should run outside Docker.

### E2E smoke

```bash
cd infra/compose
./scripts/run-e2e.sh
```

## Workflow builder docs

Operator workflow authoring guide (Quick create + Raw JSON):

- `docs/WORKFLOW_CREATION_GUIDE.md`
