/**
 * AURA Frontend — Top Header Bar.
 *
 * File: src/components/Layout/Header.jsx
 * Purpose: Shows current view title and backend status.
 */

import './Header.css'

const VIEW_TITLES = {
  chat: 'Chat with AURA',
  memory: 'Memory',
  knowledge: 'Knowledge Base',
  settings: 'Settings'
}

export default function Header ({ activeView, backendStatus }) {
  return (
    <header className='header'>
      <h1 className='header__title'>{VIEW_TITLES[activeView] || 'AURA'}</h1>
      <div className='header__meta'>
        {backendStatus === 'connected' && (
          <span className='header__model'>qwen2.5:3b</span>
        )}
      </div>
    </header>
  )
}
