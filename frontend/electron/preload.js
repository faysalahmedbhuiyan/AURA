/**
 * AURA Desktop — Electron Preload Script.
 *
 * File: electron/preload.js
 * Purpose: Secure bridge between Electron main process and React renderer.
 *          Exposes only specific, safe APIs to the renderer via contextBridge.
 *          Never expose entire Node.js or Electron APIs to renderer.
 */

const { contextBridge, ipcRenderer } = require('electron')

/**
 * Expose safe AURA APIs to renderer process.
 * Accessible in React as: window.aura.*
 */
contextBridge.exposeInMainWorld('aura', {
  // App information
  getVersion: () => ipcRenderer.invoke('get-app-version'),

  // Window controls
  minimize: () => ipcRenderer.invoke('window-minimize'),
  maximize: () => ipcRenderer.invoke('window-maximize'),
  close: () => ipcRenderer.invoke('window-close'),

  // Platform info
  platform: process.platform
})
