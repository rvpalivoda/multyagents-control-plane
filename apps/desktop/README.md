# Desktop wrapper

Electron desktop wrapper for local `multyagents` launcher commands.

## Run from repository root

```bash
./scripts/multyagents desktop
```

On first start, dependencies are installed automatically in `apps/desktop/node_modules`.
On Linux, launcher auto-falls back to `--no-sandbox` if `chrome-sandbox` is not configured as `root:root` + `4755`.

## Linux sandbox fix (optional)

If you want Chromium sandbox enabled:

```bash
sudo chown root:root apps/desktop/node_modules/electron/dist/chrome-sandbox
sudo chmod 4755 apps/desktop/node_modules/electron/dist/chrome-sandbox
```

## Direct run

```bash
cd apps/desktop
npm install
npm start
```
