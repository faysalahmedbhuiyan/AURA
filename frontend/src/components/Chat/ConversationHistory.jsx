/**
 * AURA Frontend — Conversation History.
 *
 * File: src/components/Chat/ConversationHistory.jsx
 * Purpose: ChatGPT-style conversation list in sidebar.
 *          Shows all past conversations, allows switching between them.
 */

import { useState, useEffect } from 'react'
import { getConversationList } from '../../services/api'
import './ConversationHistory.css'

export default function ConversationHistory ({ currentId, onSelect, refresh }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadConversations()
  }, [refresh])

  const loadConversations = async () => {
    setLoading(true)
    try {
      const res = await getConversationList()
      setConversations(res.data || [])
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = dateStr => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString()
  }

  const getTitle = conv => {
    if (conv.title) return conv.title
    if (conv.first_message) {
      const msg = conv.first_message
      return msg.length > 40 ? msg.slice(0, 40) + '...' : msg
    }
    return `Chat ${conv.id?.slice(0, 8) || ''}`
  }

  if (loading) {
    return (
      <div className='conv-history__loading'>
        <span>Loading...</span>
      </div>
    )
  }

  if (conversations.length === 0) {
    return (
      <div className='conv-history__empty'>
        <span>No conversations yet</span>
        <span>Start a new chat!</span>
      </div>
    )
  }

  return (
    <div className='conv-history'>
      {conversations.map(conv => (
        <button
          key={conv.id}
          className={`conv-history__item ${
            currentId === conv.id ? 'conv-history__item--active' : ''
          }`}
          onClick={() => onSelect(conv.id)}
        >
          <div className='conv-history__item-icon'>💬</div>
          <div className='conv-history__item-content'>
            <div className='conv-history__item-title'>{getTitle(conv)}</div>
            <div className='conv-history__item-meta'>
              {formatDate(conv.updated_at)}
              {conv.message_count > 0 && (
                <span> · {conv.message_count} msgs</span>
              )}
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
