/**
 * AURA Frontend — Root Application Component.
 *
 * File: src/App.jsx
 * Purpose: Root component managing global layout and routing.
 *          Handles backend connection status check on mount.
 */

import { useState, useEffect } from 'react'
import { checkHealth } from './services/api'
import ChatWindow from './components/Chat/ChatWindow'
import KnowledgeView from './components/Knowledge/KnowledgeView'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import AgentView from './components/Agents/AgentView'
import ReviewView from './components/Review/ReviewView'
import './App.css'

export default function App () {
  const [backendStatus, setBackendStatus] = useState('checking')
  const [activeView, setActiveView] = useState('chat')
  const [currentConversationId, setCurrentConversationId] = useState(null)

  // Check backend connection on startup
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await checkHealth()
        setBackendStatus('connected')
      } catch {
        setBackendStatus('disconnected')
      }
    }
    checkBackend()
    // Recheck every 30 seconds
    const interval = setInterval(checkBackend, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleNewConversation = () => {
    setCurrentConversationId(null)
  }

  return (
    <div className='app'>
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        onNewConversation={handleNewConversation}
        backendStatus={backendStatus}
      />
      <div className='app__main'>
        <Header activeView={activeView} backendStatus={backendStatus} />
        <div className='app__content'>
          {backendStatus === 'disconnected' ? (
            <div className='app__error'>
              <div className='app__error-icon'>⚠️</div>
              <h2>Backend Disconnected</h2>
              <p>AURA backend is not running.</p>
              <code>
                cd D:\AURA\backend && uvicorn app.main:app --host 127.0.0.1
                --port 8000 --reload
              </code>
            </div>
          ) : activeView === 'knowledge' ? (
            <KnowledgeView />
          ) : activeView === 'memory' ? (
            <AgentView />
          ) : activeView === 'settings' ? (
            <ReviewView />
          ) : (
            <ChatWindow
              conversationId={currentConversationId}
              onConversationStart={setCurrentConversationId}
            />
          )}
        </div>
      </div>
    </div>
  )
}
