import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * Vite configuration for AURA Frontend.
 *
 * Purpose: Configure Vite bundler for React + Electron.
 * - base: './' ensures Electron can load assets from relative paths
 * - server port: 5173 (matched in electron dev wait-on)
 * - outDir: dist (electron-builder reads from here)
 */
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    strictPort: true
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
