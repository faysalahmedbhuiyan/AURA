/**
 * AURA Frontend — React Entry Point.
 *
 * File: src/main.jsx
 * Purpose: Mounts the React application to the DOM.
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)
