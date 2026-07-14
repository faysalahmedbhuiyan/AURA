/**
 * AURA Frontend — Dev Mode.
 *
 * File: src/components/DevMode/DevMode.jsx
 * Purpose: Advanced features panel — hidden by default.
 *          Access via "Dev Mode" button in sidebar.
 */

import { useState } from 'react'
import KnowledgeView from '../Knowledge/KnowledgeView'
import AgentView from '../Agents/AgentView'
import RollbackView from '../Rollback/RollbackView'
import UnderstandingView from '../Understanding/UnderstandingView'
import ResearchView from '../Research/ResearchView'
import './DevMode.css'

const DEV_TABS = [
  { id: 'agents', icon: '🤖', label: 'Agents' },
  { id: 'research', icon: '🔍', label: 'Research' },
  { id: 'knowledge', icon: '📚', label: 'Knowledge' },
  { id: 'rollback', icon: '↩', label: 'Rollback' },
  { id: 'understanding', icon: '🔬', label: 'Understand' }
]

export default function DevMode ({ onClose }) {
  const [activeTab, setActiveTab] = useState('agents')

  const renderTab = () => {
    switch (activeTab) {
      case 'agents':
        return <AgentView />
      case 'research':
        return <ResearchView />
      case 'knowledge':
        return <KnowledgeView />
      case 'rollback':
        return <RollbackView />
      case 'understanding':
        return <UnderstandingView />
      default:
        return null
    }
  }

  return (
    <div className='dev-mode'>
      <div className='dev-mode__header'>
        <span className='dev-mode__title'>🛠 Dev Mode</span>
        <div className='dev-mode__tabs'>
          {DEV_TABS.map(t => (
            <button
              key={t.id}
              className={`dev-mode__tab ${
                activeTab === t.id ? 'dev-mode__tab--active' : ''
              }`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
        <button className='dev-mode__close' onClick={onClose}>
          ✕ Close
        </button>
      </div>
      <div className='dev-mode__content'>{renderTab()}</div>
    </div>
  )
}
