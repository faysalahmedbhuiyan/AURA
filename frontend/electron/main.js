/**
 * AURA Desktop — Electron Main Process.
 *
 * File: electron/main.js
 * Purpose: Creates the Electron desktop window for AURA.
 *          Loads React frontend via localhost in dev mode,
 *          or from built dist/ files in production.
 *
 * Security: contextIsolation enabled, nodeIntegration disabled.
 *           All Node.js access goes through preload.js bridge.
 */

const { app, BrowserWindow, ipcMain, shell } = require('electron')
const path = require('path')

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

// ── App Lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
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
