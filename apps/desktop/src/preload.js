const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("launcherApi", {
  getMeta: () => ipcRenderer.invoke("launcher:meta"),
  run: (command) => ipcRenderer.invoke("launcher:run", command),
  stop: () => ipcRenderer.invoke("launcher:stop"),
  onOutput: (callback) => {
    const handler = (_event, payload) => callback(payload);
    ipcRenderer.on("launcher:output", handler);
    return () => ipcRenderer.removeListener("launcher:output", handler);
  }
});
