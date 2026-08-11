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

const { app, BrowserWindow, ipcMain, shell } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const fs = require('fs')

// ── Constants ─────────────────────────────────────────────────────────────────
const VITE_DEV_SERVER_URL = 'http://localhost:5173'
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

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

function startBackend () {
  // Dev mode: you start uvicorn yourself in a terminal — this function
  // does nothing then, since isDev short-circuits below in whenReady().
  // Production (packaged app): the backend folder (with its venv) must
  // be bundled alongside the app — see package.json "files" note below.
  const backendDir = path.join(process.resourcesPath, 'backend')

  const pythonExe = process.platform === 'win32'
    ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDir, 'venv', 'bin', 'python')

  if (!fs.existsSync(pythonExe)) {
    console.error('Backend venv not found at', pythonExe, '— AURA backend will not auto-start.')
    return
  }

  console.log('Starting AURA backend...')
  backendProcess = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
    { cwd: backendDir, stdio: 'inherit' }
  )

  backendProcess.on('error', (err) => {
    console.error('Failed to start AURA backend:', err)
  })

  backendProcess.on('exit', (code) => {
    console.log('AURA backend exited with code', code)
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

// ── App Lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  if (!isDev) {
    startBackend()
  }

  // Give the backend a few seconds to come up before loading the window.
  // In dev mode there's no wait — you're expected to already have
  // uvicorn running manually in a separate terminal.
  const delay = isDev ? 0 : 4000
  setTimeout(() => {
    createWindow()
  }, delay)

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