const outputEl = document.getElementById("output");
const statusLabelEl = document.getElementById("statusLabel");
const rootDirLabelEl = document.getElementById("rootDirLabel");
const clearBtnEl = document.getElementById("clearBtn");
const stopBtnEl = document.getElementById("stopBtn");
const commandButtons = Array.from(document.querySelectorAll("[data-command]"));

let running = false;

function setRunning(value) {
  running = value;
  for (const button of commandButtons) {
    button.disabled = value;
  }
  stopBtnEl.disabled = !value;
}

function appendOutput(text, cls = "") {
  const span = document.createElement("span");
  span.textContent = text;
  if (cls) {
    span.className = cls;
  }
  outputEl.appendChild(span);
  outputEl.scrollTop = outputEl.scrollHeight;
}

function setStatus(text) {
  statusLabelEl.textContent = text;
}

async function runCommand(command) {
  if (running) {
    return;
  }
  appendOutput(`\n$ ./scripts/multyagents ${command}\n`, "cmd");
  setRunning(true);
  setStatus(`running: ${command}`);

  const result = await window.launcherApi.run(command);
  const message = `\n[exit code: ${result.exitCode}${result.signal ? `, signal: ${result.signal}` : ""}]\n`;
  appendOutput(message, result.exitCode === 0 ? "ok" : "err");
  setStatus(result.exitCode === 0 ? `success: ${command}` : `failed: ${command}`);
  setRunning(false);
}

window.launcherApi.onOutput((payload) => {
  if (payload.type === "stdout") {
    appendOutput(payload.chunk);
    return;
  }
  if (payload.type === "stderr") {
    appendOutput(payload.chunk, "err");
    return;
  }
  if (payload.type === "meta") {
    appendOutput(`[${payload.message}]\n`, "meta");
  }
});

for (const button of commandButtons) {
  button.addEventListener("click", () => runCommand(button.dataset.command));
}

clearBtnEl.addEventListener("click", () => {
  outputEl.textContent = "";
});

stopBtnEl.addEventListener("click", async () => {
  const result = await window.launcherApi.stop();
  if (result.stopped) {
    appendOutput(`\n[sent SIGTERM to pid=${result.pid}]\n`, "meta");
  } else {
    appendOutput("\n[no running command]\n", "meta");
  }
});

async function init() {
  const meta = await window.launcherApi.getMeta();
  rootDirLabelEl.textContent = meta.rootDir;
  setRunning(false);
  setStatus("idle");
  appendOutput("Desktop control panel ready.\n", "meta");
}

init();
