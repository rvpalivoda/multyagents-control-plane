# host-runner

Host-side service intended to run outside Docker and invoke local `codex` CLI.

This stage includes a minimal submit/status/cancel API contract scaffold.

Shared-workspace tasks must include `workspace` payload with:
- `project_id`
- `project_root` (absolute path)
- `lock_paths` (absolute paths)

Execution mode:
- default `HOST_RUNNER_EXECUTOR=mock` runs background mock completion.
- optional `HOST_RUNNER_EXECUTOR=shell` uses `HOST_RUNNER_CMD_TEMPLATE`.
  - command template supports `{prompt}`, `{task_id}`, `{run_id}`.
- optional `HOST_RUNNER_EXECUTOR=codex` runs local Codex CLI directly:
  - command shape: `<HOST_RUNNER_CODEX_BIN> exec <HOST_RUNNER_CODEX_ARGS...> <prompt>`
  - `HOST_RUNNER_CODEX_BIN` default: `codex`
  - `HOST_RUNNER_CODEX_ARGS` default: empty string

`isolated-worktree` mode support:
- payload workspace may include:
  - `worktree_path`
  - `git_branch`
- runner performs:
  - `git worktree add --force -B <git_branch> <worktree_path> HEAD`
  - executes task in `<worktree_path>`
  - `git worktree remove --force <worktree_path>` after completion
- cleanup can be disabled with `HOST_RUNNER_CLEANUP_WORKTREE=false`

`docker-sandbox` mode support:
- submit payload must include `sandbox`:
  - `image`
  - `command` (list)
  - optional `workdir`, `env`, `mounts`
- runner executes `docker run` directly and captures stdout/stderr/exit code
- cancel endpoint force-stops active sandbox container via `docker rm -f`
- task metadata includes `container_id`

Runner callback integration:
- submit payload can include:
  - `status_callback_url`
  - `status_callback_token`
- runner emits callback updates on `running`, `success`, `failed`, `canceled`.
- callback payload also includes optional `container_id` for docker-sandbox tasks.
- callback header is `X-Runner-Token` when token is provided.
