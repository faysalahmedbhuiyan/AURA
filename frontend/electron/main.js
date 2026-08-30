/**
 * AURA Desktop — Electron Main Process.
 *
 * File: electron/main.js
 * Purpose: Creates the Electron desktop window for AURA, and starts/stops
 *          a fully self-contained Python backend (no dependency on any
 *          Python being installed on the target machine — see
 *          findBackendPython below and scripts/build_portable_python.ps1).
 *
 * Security: contextIsolation enabled, nodeIntegration disabled.
 *           All Node.js access goes through preload.js bridge.
 */

const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const fs = require('fs')
const http = require('http')

// ── Constants ─────────────────────────────────────────────────────────────────
const VITE_DEV_SERVER_URL = 'http://localhost:5173'
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const BACKEND_HEALTH_URL = 'http://127.0.0.1:8000/api/v1/health'
// First run can be slow (model presence checks / background downloads
// kicked off at startup) — poll instead of a fixed short delay.
const BACKEND_WAIT_TIMEOUT_MS = 120000
const BACKEND_POLL_INTERVAL_MS = 500

// ── Backend log file (so a crash is diagnosable even with no console —
// double-clicking the installed app has none) ─────────────────────────────
const LOG_DIR = app.getPath('userData')
const BACKEND_LOG_PATH = path.join(LOG_DIR, 'backend.log')

function appendLog (line) {
  try {
    fs.mkdirSync(LOG_DIR, { recursive: true })
    fs.appendFileSync(
      BACKEND_LOG_PATH,
      `[${new Date().toISOString()}] ${line}\n`
    )
  } catch (e) {
    console.error('Could not write to backend log:', e)
  }
}

// ── Window Management ─────────────────────────────────────────────────────────
let mainWindow = null

function createWindow () {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'AURA — Personal AI Operating System',
    backgroundColor: '#0f0f0f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
    frame: true,
    show: false
  })

  if (isDev) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    mainWindow.focus()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── Backend Process Management ──────────────────────────────────────────────
let backendProcess = null

/**
 * Look for a Python interpreter to run the backend with, in priority order:
 *   1. python-portable/  — a fully self-contained embeddable Python built by
 *      scripts/build_portable_python.ps1. Does NOT depend on anything being
 *      installed on the target machine. THIS is what should ship in a real
 *      installer handed to another PC.
 *   2. venv/ or .venv/   — a normal virtualenv. Only works if that exact
 *      Python version is ALSO installed on this machine at the recorded
 *      path (venv/pyvenv.cfg) — i.e. dev-machine-only, NOT portable to
 *      another PC. Kept as a fallback for local dev/testing only.
 */
function findBackendPython (backendDir) {
  const exe = process.platform === 'win32' ? 'python.exe' : 'python'
  const candidates =
    process.platform === 'win32'
      ? [
          path.join(backendDir, 'python-portable', exe),
          path.join(backendDir, 'venv', 'Scripts', exe),
          path.join(backendDir, '.venv', 'Scripts', exe)
        ]
      : [
          path.join(backendDir, 'python-portable', 'bin', exe),
          path.join(backendDir, 'venv', 'bin', exe),
          path.join(backendDir, '.venv', 'bin', exe)
        ]

  return candidates.find(p => fs.existsSync(p)) || null
}

function showBackendMissingDialog (backendDir) {
  dialog.showErrorBox(
    'AURA Backend Not Found',
    `AURA couldn't find a Python runtime inside:\n${backendDir}\n\n` +
      `This build wasn't packaged with a self-contained Python. Run ` +
      `scripts/build_portable_python.ps1 from the backend/ folder BEFORE ` +
      `running electron-builder — this creates backend/python-portable, ` +
      `which is what actually ships inside the installer.\n\n` +
      `AURA will keep running, but chat/image/voice features won't work ` +
      `until this is fixed.`
  )
}

function showBackendCrashedDialog (code) {
  dialog.showErrorBox(
    'AURA Backend Stopped Unexpectedly',
    `The AURA backend process exited (code ${code}) shortly after starting.\n\n` +
      `The exact error has been saved to:\n${BACKEND_LOG_PATH}\n\n` +
      `Open that file for the real Python traceback — "exit code ${code}" ` +
      `alone doesn't say what failed.`
  )
}

function startBackend () {
  const backendDir = path.join(process.resourcesPath, 'backend')
  const pythonExe = findBackendPython(backendDir)

  if (!pythonExe) {
    console.error('Backend Python not found under', backendDir)
    showBackendMissingDialog(backendDir)
    return
  }

  appendLog(`Starting backend using ${pythonExe}`)
  backendProcess = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: backendDir,
      env: {
        ...process.env,
        // Belt-and-suspenders alongside the ".." entry build_portable_python.ps1
        // adds to python311._pth - embeddable Python doesn't add the CWD to
        // sys.path automatically, so without one of these two fixes uvicorn
        // can't find AURA's own "app" package no matter what directory it's
        // launched from.
        PYTHONPATH: backendDir
      }
    }
  )

  backendProcess.stdout.on('data', data =>
    appendLog(`[stdout] ${data}`.trimEnd())
  )
  backendProcess.stderr.on('data', data =>
    appendLog(`[stderr] ${data}`.trimEnd())
  )

  let startupGracePeriodOver = false
  setTimeout(() => {
    startupGracePeriodOver = true
  }, 5000)

  backendProcess.on('error', err => {
    appendLog(`Failed to start backend: ${err}`)
    dialog.showErrorBox('AURA Backend Failed to Start', String(err))
  })

  backendProcess.on('exit', code => {
    appendLog(`Backend exited with code ${code}`)
    if (!startupGracePeriodOver && code !== 0 && code !== null) {
      showBackendCrashedDialog(code)
    }
    backendProcess = null
  })
}

function stopBackend () {
  if (backendProcess) {
    appendLog('Stopping backend...')
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t'])
    } else {
      backendProcess.kill()
    }
    backendProcess = null
  }
}

/** Polls the backend's health endpoint instead of a fixed delay — first
 * run can be slower than a few seconds (model checks / background
 * downloads kicked off at startup). */
function waitForBackend (timeoutMs) {
  return new Promise(resolve => {
    const startedAt = Date.now()

    const poll = () => {
      const req = http.get(BACKEND_HEALTH_URL, { timeout: 2000 }, res => {
        res.resume()
        resolve(true)
      })
      req.on('error', retry)
      req.on('timeout', () => {
        req.destroy()
        retry()
      })
    }

    const retry = () => {
      if (Date.now() - startedAt >= timeoutMs) {
        resolve(false)
        return
      }
      setTimeout(poll, BACKEND_POLL_INTERVAL_MS)
    }

    poll()
  })
}

// ── App Lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  if (isDev) {
    createWindow()
    return
  }

  startBackend()

  const backendReady = await waitForBackend(BACKEND_WAIT_TIMEOUT_MS)
  if (!backendReady) {
    appendLog(
      `Backend did not respond to health check within ${BACKEND_WAIT_TIMEOUT_MS}ms`
    )
    dialog.showErrorBox(
      'AURA Backend Is Taking Too Long',
      `The backend did not respond in time. AURA will still open, but ` +
        `chat/image/voice features may not work yet.\n\nLog file:\n${BACKEND_LOG_PATH}`
    )
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopBackend()
})

// ── IPC Handlers ─────────────────────────────────────────────────────────────
ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})

ipcMain.handle('window-minimize', () => {
  mainWindow?.minimize()
})

ipcMain.handle('window-maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize()
  } else {
    mainWindow?.maximize()
  }
})

ipcMain.handle('window-close', () => {
  mainWindow?.close()
})
