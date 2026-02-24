const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

const ROOT_DIR = path.resolve(__dirname, "../../..");
const LAUNCHER_PATH = path.join(ROOT_DIR, "scripts", "multyagents");
const ALLOWED_COMMANDS = new Set(["up", "down", "status", "logs", "e2e"]);

let mainWindow = null;
let activeProcess = null;

function sendOutput(event, payload) {
  event.sender.send("launcher:output", payload);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1120,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "index.html"));
}

function runLauncherCommand(event, command) {
  if (!ALLOWED_COMMANDS.has(command)) {
    return { exitCode: 2, error: `unsupported command: ${command}` };
  }
  if (!fs.existsSync(LAUNCHER_PATH)) {
    return { exitCode: 2, error: `launcher not found: ${LAUNCHER_PATH}` };
  }
  if (activeProcess) {
    return { exitCode: 3, error: "another command is already running" };
  }

  return new Promise((resolve) => {
    const startedAt = new Date().toISOString();
    sendOutput(event, { type: "meta", message: `Running: ${command}`, startedAt });

    const child = spawn("bash", [LAUNCHER_PATH, command], {
      cwd: ROOT_DIR,
      env: process.env
    });
    activeProcess = child;

    child.stdout.on("data", (chunk) => {
      sendOutput(event, { type: "stdout", chunk: chunk.toString() });
    });
    child.stderr.on("data", (chunk) => {
      sendOutput(event, { type: "stderr", chunk: chunk.toString() });
    });
    child.on("error", (error) => {
      sendOutput(event, { type: "stderr", chunk: `${error.message}\n` });
    });
    child.on("close", (code, signal) => {
      activeProcess = null;
      const finishedAt = new Date().toISOString();
      sendOutput(event, {
        type: "meta",
        message: `Finished: ${command} (exit=${code ?? 1}${signal ? `, signal=${signal}` : ""})`,
        finishedAt
      });
      resolve({ exitCode: code ?? 1, signal: signal ?? null, command, startedAt, finishedAt });
    });
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("launcher:meta", () => {
  return {
    rootDir: ROOT_DIR,
    commands: Array.from(ALLOWED_COMMANDS)
  };
});

ipcMain.handle("launcher:run", (event, command) => {
  return runLauncherCommand(event, command);
});

ipcMain.handle("launcher:stop", () => {
  if (!activeProcess) {
    return { stopped: false };
  }
  const pid = activeProcess.pid;
  const stopped = activeProcess.kill("SIGTERM");
  return { stopped, pid };
});
