/**
 * AURA Desktop — Electron Main Process.
 *
 * File: electron/main.js
 * Purpose: Creates the Electron desktop window for AURA.
 *          Loads React frontend via localhost in dev mode,
 *          or from built dist/ files in production.
 *          Also starts/stops the Python backend automatically so the
 *          whole app works from a single click (dev mode still needs
 *          uvicorn started manually — see note below).
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
// First run can be slow (model checks / background downloads kicked off
// at startup) — poll instead of a fixed short delay, but still cap it so
// a genuinely broken backend doesn't hang the window forever.
const BACKEND_WAIT_TIMEOUT_MS = 120000
const BACKEND_POLL_INTERVAL_MS = 500

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
      contextIsolation: true, // Security: isolate renderer
      nodeIntegration: false, // Security: no Node in renderer
      sandbox: false // Required for preload access
    },
    // Window frame styling
    frame: true,
    show: false // Show after ready-to-show
  })

  // Load frontend
  if (isDev) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // Show window when fully loaded (prevents white flash)
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    mainWindow.focus()
  })

  // Open external links in browser, not Electron
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

/** Tries a few common venv layouts, not just "venv" — some setups use
 * ".venv" or a Linux/macOS layout even inside a Windows-target build
 * folder during dev testing. Returns the first python executable found,
 * or null if none of them exist. */
function findBackendPython (backendDir) {
  const candidates =
    process.platform === 'win32'
      ? [
          path.join(backendDir, 'venv', 'Scripts', 'python.exe'),
          path.join(backendDir, '.venv', 'Scripts', 'python.exe')
        ]
      : [
          path.join(backendDir, 'venv', 'bin', 'python'),
          path.join(backendDir, '.venv', 'bin', 'python')
        ]

  return candidates.find(p => fs.existsSync(p)) || null
}

function showBackendMissingDialog (backendDir) {
  dialog.showErrorBox(
    'AURA Backend Not Found',
    `AURA couldn't find a Python environment inside:\n${backendDir}\n\n` +
      `This means the app was built without a "venv" folder bundled inside ` +
      `backend/. Before building the installer, run (from the backend/ folder):\n\n` +
      `  python -m venv venv\n` +
      `  venv\\Scripts\\activate\n` +
      `  pip install -r requirements.txt\n\n` +
      `Then rebuild the installer. AURA will keep running, but chat/image/` +
      `voice features won't work until the backend can start.`
  )
}

function showBackendCrashedDialog (code) {
  dialog.showErrorBox(
    'AURA Backend Stopped Unexpectedly',
    `The AURA backend process exited (code ${code}) shortly after starting.\n\n` +
      `Check that all dependencies are installed in backend/venv ` +
      `(pip install -r requirements.txt), and that no other app is already ` +
      `using port 8000.`
  )
}

function startBackend () {
  // Dev mode: you start uvicorn yourself in a terminal — this function
  // does nothing then, since isDev short-circuits below in whenReady().
  // Production (packaged app): the backend folder (with its venv) must
  // be bundled alongside the app — see package.json "files" note below.
  const backendDir = path.join(process.resourcesPath, 'backend')
  const pythonExe = findBackendPython(backendDir)

  if (!pythonExe) {
    console.error(
      'Backend venv not found under',
      backendDir,
      '— AURA backend will not auto-start.'
    )
    showBackendMissingDialog(backendDir)
    return
  }

  console.log('Starting AURA backend using', pythonExe)
  backendProcess = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
    { cwd: backendDir, stdio: 'inherit' }
  )

  let startupGracePeriodOver = false
  setTimeout(() => {
    startupGracePeriodOver = true
  }, 5000)

  backendProcess.on('error', err => {
    console.error('Failed to start AURA backend:', err)
    dialog.showErrorBox('AURA Backend Failed to Start', String(err))
  })

  backendProcess.on('exit', code => {
    console.log('AURA backend exited with code', code)
    // Only alarm the user if it died right after starting (a real crash),
    // not on the normal shutdown that happens when the window closes.
    if (!startupGracePeriodOver && code !== 0 && code !== null) {
      showBackendCrashedDialog(code)
    }
    backendProcess = null
  })
}

function stopBackend () {
  if (backendProcess) {
    console.log('Stopping AURA backend...')
    if (process.platform === 'win32') {
      // taskkill needed on Windows to kill the whole process tree
      // (uvicorn's child processes otherwise survive).
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t'])
    } else {
      backendProcess.kill()
    }
    backendProcess = null
  }
}

/** Polls the backend's health endpoint instead of a fixed delay — first
 * run can be slower than 4s (model presence checks, possibly kicking off
 * a background download), so a fixed short wait caused the exact
 * "ERR_CONNECTION_REFUSED on first load" symptom even when the backend
 * WAS starting fine, just not fast enough yet. */
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
    console.error(
      'Backend did not respond to health check within',
      BACKEND_WAIT_TIMEOUT_MS,
      'ms'
    )
    dialog.showErrorBox(
      'AURA Backend Is Taking Too Long',
      'The backend did not respond in time. AURA will still open, but ' +
        'chat/image/voice features may not work until it finishes starting ' +
        '(or fails — check the previous error dialog, if any).'
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
/**
 * Handle app version request from renderer.
 */
ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})

/**
 * Handle window control requests from renderer.
 */
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
