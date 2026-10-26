const { app, BrowserWindow, shell, protocol, net } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const { spawn, spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

// Use a standard secure custom scheme instead of file:// (opaque origin), so
// the host FastAPI app can explicitly allow the desktop app's CORS origin.
protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true } },
]);

// The studio UI talks to the local OCR API (default endpoint in src/main.jsx). The desktop app starts
// and stops that API itself so launching the app is enough; an API that is already running is reused.
const API_HOST = '127.0.0.1';
const API_PORT = Number(process.env.MEDINTEL_API_PORT || 8000);
const API_URL = `http://${API_HOST}:${API_PORT}`;
const BACKEND_DIR = path.resolve(__dirname, 'backend');
const STARTUP_TIMEOUT_MS = 5 * 60 * 1000; // first start loads TrOCR-large and PP-OCR models

let backendProcess = null;
let backendLogPath = null;

async function registerAppProtocol() {
  const root = path.resolve(__dirname, 'dist');
  protocol.handle('app', async (request) => {
    const url = new URL(request.url);
    const requestedPath = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
    const filePath = path.resolve(root, `.${requestedPath}`);
    if (filePath !== root && !filePath.startsWith(root + path.sep)) {
      return new Response('Not found', { status: 404 });
    }
    try {
      return await net.fetch(pathToFileURL(filePath).toString());
    } catch {
      return new Response('Not found', { status: 404 });
    }
  });
}

async function apiIsUp() {
  try {
    const res = await net.fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

function pythonCandidates() {
  const venvPython = process.platform === 'win32'
    ? path.join(BACKEND_DIR, '.venv', 'Scripts', 'python.exe')
    : path.join(BACKEND_DIR, '.venv', 'bin', 'python');
  const candidates = [];
  if (process.env.MEDINTEL_PYTHON) candidates.push([process.env.MEDINTEL_PYTHON, []]);
  if (fs.existsSync(venvPython)) candidates.push([venvPython, []]);
  candidates.push(['python', []]);
  if (process.platform === 'win32') candidates.push(['py', ['-3']]);
  else candidates.push(['python3', []]);
  return candidates;
}

// First interpreter that can import the API's own dependencies.
function findPython() {
  for (const [cmd, prefix] of pythonCandidates()) {
    const probe = spawnSync(cmd, [...prefix, '-c', 'import uvicorn, fastapi, cv2, transformers'], {
      cwd: BACKEND_DIR, windowsHide: true, timeout: 60000,
    });
    if (probe.status === 0) return [cmd, prefix];
  }
  return null;
}

function startBackend() {
  if (!fs.existsSync(path.join(BACKEND_DIR, 'app', 'main.py'))) {
    return 'The OCR backend folder was not found next to the desktop app.';
  }
  const python = findPython();
  if (!python) {
    return 'No Python environment with the OCR dependencies was found. Run setup-windows.cmd, '
      + 'or set MEDINTEL_PYTHON to a Python that has backend/requirements-original.txt installed.';
  }
  const [cmd, prefix] = python;
  backendLogPath = path.join(app.getPath('userData'), 'backend.log');
  const log = fs.openSync(backendLogPath, 'a');
  fs.writeSync(log, `\n=== ${new Date().toISOString()} starting OCR API with ${cmd} ${prefix.join(' ')}\n`);
  backendProcess = spawn(cmd, [...prefix, '-m', 'uvicorn', 'app.main:app', '--host', API_HOST, '--port', String(API_PORT)], {
    cwd: BACKEND_DIR,
    windowsHide: true,
    stdio: ['ignore', log, log],
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  });
  backendProcess.on('exit', (code) => {
    fs.appendFileSync(backendLogPath, `=== OCR API exited with code ${code}\n`);
    backendProcess = null;
  });
  return null;
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

function statusPage(title, detail, showContinue) {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>MedIntel AI OCR Studio</title>
<style>body{margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#f5f7fb;
font-family:"Segoe UI",system-ui,sans-serif;color:#1d2433}.card{max-width:560px;padding:32px 36px;background:#fff;
border-radius:12px;box-shadow:0 8px 30px rgba(20,30,60,.08)}h1{font-size:20px;margin:0 0 10px}p{margin:0 0 12px;
line-height:1.5;color:#4a5468}a{color:#2456d6;font-weight:600}</style></head><body><div class="card">
<h1>${esc(title)}</h1><p>${esc(detail)}</p>${showContinue ? '<p><a href="app://medintel/index.html">Continue to OCR Studio</a></p>' : ''}
</div></body></html>`;
  return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`;
}

async function waitForBackend() {
  const started = Date.now();
  while (Date.now() - started < STARTUP_TIMEOUT_MS) {
    if (await apiIsUp()) return true;
    if (!backendProcess) return false; // process exited during start-up
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 1080,
    minHeight: 720,
    title: 'MedIntel AI OCR Studio',
    backgroundColor: '#f5f7fb',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      devTools: !app.isPackaged,
    },
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith('app://medintel/')) event.preventDefault();
  });
  return win;
}

async function openStudio(win) {
  if (await apiIsUp()) {
    win.loadURL('app://medintel/index.html');
    return;
  }
  const error = backendProcess ? null : startBackend();
  if (error) {
    win.loadURL(statusPage('OCR engine could not be started', error, true));
    return;
  }
  win.loadURL(statusPage('Starting the OCR engine…',
    'Loading the handwriting and printed-text models. The first start can take up to a minute.', false));
  if (await waitForBackend()) {
    win.loadURL('app://medintel/index.html');
  } else {
    win.loadURL(statusPage('OCR engine did not start',
      `The OCR API did not become ready. Details are in ${backendLogPath}.`, true));
  }
}

app.whenReady().then(async () => {
  await registerAppProtocol();
  await openStudio(createWindow());
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) openStudio(createWindow());
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', stopBackend);
