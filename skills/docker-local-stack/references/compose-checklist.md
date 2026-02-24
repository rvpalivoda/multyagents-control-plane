# Compose Checklist

## Required services

- `ui`
- `api`
- `postgres`
- `redis`
- `telegram-bot`

## Required checks

- Healthchecks pass
- API can reach DB and Redis
- UI can reach API
- Bot can reach API
- Persistent volumes mounted
