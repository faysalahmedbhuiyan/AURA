/**
 * AURA Frontend — Root Application Component v2.
 *
 * File: src/App.jsx
 * Purpose: JARVIS-style interface — chat first, everything else hidden.
 *          Conversation history in sidebar (ChatGPT style).
 *          Dev mode for advanced features.
 */

import { useState, useEffect } from 'react'
import { checkHealth } from './services/api'
import ChatWindow from './components/Chat/ChatWindow'
import ConversationHistory from './components/Chat/ConversationHistory'
import DevMode from './components/DevMode/DevMode'
import ResearchView from './components/Research/ResearchView'
import './App.css'

export default function App () {
  const [backendStatus, setBackendStatus] = useState('checking')
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [devMode, setDevMode] = useState(false)
  const [refreshHistory, setRefreshHistory] = useState(0)

  useEffect(() => {
    const check = async () => {
      try {
        await checkHealth()
        setBackendStatus('connected')
      } catch {
        setBackendStatus('disconnected')
      }
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleNewConversation = () => {
    setCurrentConversationId(null)
  }

  const handleConversationStart = id => {
    setCurrentConversationId(id)
    setRefreshHistory(n => n + 1)
  }

  return (
    <div className='app'>
      {/* Sidebar — Conversation History */}
      <aside className='app__sidebar'>
        {/* Logo */}
        <div className='app__logo'>
          <span className='app__logo-icon'>◈</span>
          <span className='app__logo-text'>AURA</span>
          <span
            className={`app__status-dot ${
              backendStatus === 'connected'
                ? 'app__status-dot--ok'
                : backendStatus === 'checking'
                ? 'app__status-dot--checking'
                : 'app__status-dot--error'
            }`}
            title={backendStatus}
          />
        </div>

        {/* New Chat */}
        <button className='app__new-chat' onClick={handleNewConversation}>
          <span>＋</span> New Chat
        </button>

        {/* Conversation History */}
        <ConversationHistory
          currentId={currentConversationId}
          onSelect={setCurrentConversationId}
          refresh={refreshHistory}
        />

        {/* Bottom — Dev Mode + Settings */}
        <div className='app__sidebar-bottom'>
          <button
            className={`app__dev-btn ${devMode ? 'app__dev-btn--active' : ''}`}
            onClick={() => setDevMode(v => !v)}
          >
            🛠 Dev Mode
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <main className='app__main'>
        {devMode ? (
          <DevMode onClose={() => setDevMode(false)} />
        ) : backendStatus === 'disconnected' ? (
          <div className='app__disconnected'>
            <div className='app__disconnected-icon'>◈</div>
            <h2>AURA Offline</h2>
            <p>Backend চালু নেই।</p>
            <code>
              cd D:\AURA\backend{'\n'}
              .\venv\Scripts\Activate.ps1{'\n'}
              uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
            </code>
          </div>
        ) : (
          <ChatWindow
            conversationId={currentConversationId}
            onConversationStart={handleConversationStart}
          />
        )}
      </main>
    </div>
  )
}
