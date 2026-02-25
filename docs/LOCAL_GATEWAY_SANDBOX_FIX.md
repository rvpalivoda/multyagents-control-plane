# Local Runbook: Gateway/WebSocket 1006 + Sandbox `index.lock` Issues

## Purpose

Stabilize local multi-agent operation when you see:
- `gateway/websocket closed (1006)`
- `fatal: Unable to create .../.git/worktrees/.../index.lock: Permission denied`

---

## A) Fast recovery (2 minutes)

### 1) Restart gateway

```bash
openclaw gateway restart
openclaw gateway status
openclaw status
```

Expected: gateway is running and healthy.

### 2) Reattach Browser Relay (Chrome)

1. Open `chrome://extensions`
2. Ensure **OpenClaw Browser Relay** is enabled
3. Open target tab (e.g. GitHub)
4. Click relay icon on that tab until badge is **ON**
5. Keep the tab open during long tasks

### 3) Re-run one smoke action

Use a quick action (status/snapshot) before launching long jobs.

---

## B) Root cause and permanent fix

### Problem 1: WebSocket `1006`

Typical causes:
- gateway restarted during active session
- browser tab/relay detached
- network sleep/VPN/proxy interruption

Mitigations:
- do not sleep/hibernate machine during long runs
- keep relay tab attached and visible
- avoid unstable VPN routes for long websocket sessions

### Problem 2: `index.lock` in sandbox

Root cause:
- coding agent in sandbox cannot write `.git/worktrees/...` metadata.

Mitigations:
- run coding agents in environment with writable git metadata (host context)
- keep worktrees on writable filesystem (`/tmp/...` is fine)
- if agent still cannot commit, apply patch manually in main repo and commit there

---

## C) Recommended operating mode (stable)

1. Spawn agents in separate worktrees for parallelism
2. Allow them to implement code/tests/docs
3. Always be ready to manually integrate to `master` if sandbox commit is blocked
4. Send immediate status alerts on every completed session

---

## D) Manual integration fallback (when commit fails)

From main repo:

```bash
# Inspect changed files
cd ~/code/multyagents.dev
cd /tmp/multyagents-task-XYZ && git diff --name-only

# Copy/apply changes into main repo
# (file-by-file cp OR patch with git apply --3way)

# Validate
cd ~/code/multyagents.dev/apps/api && .venv/bin/pytest -q
cd ~/code/multyagents.dev/apps/ui && npm test && npm run build

# Commit & push in main repo
git add ...
git commit -m "feat(task-XYZ): ..."
git push
```

---

## E) Verification checklist (after fix)

- [ ] `openclaw gateway status` healthy
- [ ] Browser relay badge ON on active tab
- [ ] At least one short browser action succeeds
- [ ] Agent sessions complete without ws disconnect
- [ ] If sandbox commit fails, manual integration flow works end-to-end

---

## F) Escalation data to collect

If issue repeats, capture:

```bash
openclaw gateway status
openclaw status
```

And note:
- timestamp of disconnect
- whether relay badge was ON
- whether VPN/proxy/sleep event happened
- exact error line (`1006`, `index.lock`, etc.)

This is enough for deterministic troubleshooting.
