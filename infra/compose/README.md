# Local Compose Stack

Preferred entrypoint from repository root:

```bash
./scripts/multyagents up
```

## Services

- `postgres` on `${POSTGRES_PORT:-45432}`
- `redis` on `${REDIS_PORT:-46379}`
- `api` on `${API_PORT:-48000}`
- `ui` on `${UI_PORT:-45173}`
- `telegram-bot` on `${TELEGRAM_BOT_PORT:-48010}`

`host-runner` is intentionally not part of compose and should run on host, default `http://host.docker.internal:48070`.

## Usage

```bash
cd infra/compose
cp .env.example .env
docker compose up --build
```

Defaults are intentionally shifted to less commonly used high ports. You can still override in `.env` if needed.

CORS overrides for API (optional):

- `API_CORS_ALLOW_ORIGIN_REGEX` (default in API: `^https?://(localhost|127\.0\.0\.1)(:\d+)?$`)
- `API_CORS_ALLOW_ORIGINS` (comma-separated fixed origins, default in API: `null`)

## End-to-End Smoke

One-command E2E run (starts host-runner mock + compose stack, runs workflow scenario, then cleans up):

```bash
cd infra/compose
./scripts/run-e2e.sh
```

Optional overrides:

- `HOST_RUNNER_PORT` (default `48070`)
- `E2E_API_BASE` (default `http://localhost:48000`)
- `E2E_TIMEOUT_SECONDS` (default `90`)
- `RUNNER_LOG` (default `/tmp/multyagents-host-runner.log`)

## Validate config

```bash
cd infra/compose
docker compose config
```
