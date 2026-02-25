# telegram-bot

Bootstrap service for Telegram control channel.

This stage provides:
- `GET /health`
- `GET /config`
- `GET /telegram/commands`
- `POST /telegram/command`
- `POST /telegram/webhook`

Supported commands:
- `/run <workflow_template_id>`
- `/status <run_id>` (returns run state plus recovery hints when failed)
- `/next <run_id>`
- `/cancel <task_id>`
- `/approve <approval_id>`
- `/pause <run_id>`
- `/resume <run_id>`
- `/abort <run_id>`
