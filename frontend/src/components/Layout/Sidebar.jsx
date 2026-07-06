/**
 * AURA Frontend — Sidebar Navigation.
 *
 * File: src/components/Layout/Sidebar.jsx
 * Purpose: Left sidebar with navigation, backend status indicator,
 *          and new conversation button.
 */

import './Sidebar.css'

const NAV_ITEMS = [
  { id: 'chat', icon: '💬', label: 'Chat' },
  { id: 'memory', icon: '🧠', label: 'Memory' },
  { id: 'knowledge', icon: '📚', label: 'Knowledge' },
  { id: 'settings', icon: '⚙️', label: 'Settings' }
]

export default function Sidebar ({
  activeView,
  onViewChange,
  onNewConversation,
  backendStatus
}) {
  const statusColor = {
    connected: '#4caf7d',
    disconnected: '#e74c3c',
    checking: '#f5a623'
  }[backendStatus]

  const statusLabel = {
    connected: 'Connected',
    disconnected: 'Disconnected',
    checking: 'Connecting...'
  }[backendStatus]

  return (
    <aside className='sidebar'>
      {/* Logo */}
      <div className='sidebar__logo'>
        <span className='sidebar__logo-icon'>◈</span>
        <span className='sidebar__logo-text'>AURA</span>
      </div>

      {/* New Chat Button */}
      <button
        className='sidebar__new-chat'
        onClick={onNewConversation}
        title='New Conversation'
      >
        <span>+</span>
        <span>New Chat</span>
      </button>

      {/* Navigation */}
      <nav className='sidebar__nav'>
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            className={`sidebar__nav-item ${
              activeView === item.id ? 'sidebar__nav-item--active' : ''
            }`}
            onClick={() => onViewChange(item.id)}
          >
            <span className='sidebar__nav-icon'>{item.icon}</span>
            <span className='sidebar__nav-label'>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Backend Status */}
      <div className='sidebar__status'>
        <span
          className='sidebar__status-dot'
          style={{ background: statusColor }}
        />
        <span className='sidebar__status-label'>{statusLabel}</span>
      </div>

      {/* Version */}
      <div className='sidebar__version'>AURA v0.5.0</div>
    </aside>
  )
}
