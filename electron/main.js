const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

const PORT = 8137;
let serverProc = null;
let win = null;

function resourcesDir() {
  // electron-builder copies dist-desktop/resources into process.resourcesPath
  const base = app.isPackaged ? process.resourcesPath : path.join(__dirname, "..", "dist-desktop", "resources");
  return base;
}

function startServer() {
  const bin = path.join(resourcesDir(), "BioSyntheticaServer");
  serverProc = spawn(bin, [], {
    env: { ...process.env, PORT: String(PORT) },
    stdio: "ignore",
  });
}

function waitForServer(retries = 60) {
  return new Promise((resolve, reject) => {
    const attempt = (n) => {
      const req = http.get(`http://127.0.0.1:${PORT}/api/health`, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => {
        if (n <= 0) return reject(new Error("Server did not start"));
        setTimeout(() => attempt(n - 1), 500);
      });
    };
    attempt(retries);
  });
}

async function createWindow() {
  win = new BrowserWindow({
    width: 1360,
    height: 880,
    minWidth: 980,
    minHeight: 640,
    backgroundColor: "#070b14",
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true },
  });
  await win.loadURL(`http://127.0.0.1:${PORT}`);
}

app.whenReady().then(async () => {
  startServer();
  try {
    await waitForServer();
    await createWindow();
  } catch (err) {
    const { dialog } = require("electron");
    dialog.showErrorBox("BioSynthetica", "The research engine failed to start:\n" + err.message);
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (serverProc) serverProc.kill();
  app.quit();
});
