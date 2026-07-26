/**
 * AURA Frontend — Chat Window v2.
 *
 * File: src/components/Chat/ChatWindow.jsx
 * Purpose: Main JARVIS-style chat interface. Loads existing conversation
 *          history when switching chats. Supports attach-a-file flow:
 *          a staged file shows as a bubble, and the next message becomes
 *          an instruction about it.
 */

import { useState, useEffect, useRef } from 'react'
import {
  sendMessage,
  getConversation,
  textToSpeech,
  createConversation
} from '../../services/api'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import './ChatWindow.css'

export default function ChatWindow ({ conversationId, onConversationStart }) {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [currentConvId, setCurrentConvId] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (conversationId && conversationId !== currentConvId) {
      setCurrentConvId(conversationId)
      loadConversation(conversationId)
    } else if (!conversationId && currentConvId !== null) {
      setMessages([])
      setCurrentConvId(null)
      setError(null)
    }
  }, [conversationId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadConversation = async id => {
    setLoadingHistory(true)
    setError(null)
    setMessages([])
    try {
      const res = await getConversation(id)
      const data = res.data
      if (!data || !data.messages) {
        setError('Conversation not found.')
        return
      }
      const loaded = data.messages.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp
      }))
      setMessages(loaded)
    } catch (e) {
      console.error('Load conversation error:', e)
      setError('কথোপকথন load করা যাচ্ছে না।')
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleSend = async (text, language = 'en', viaVoice = false) => {
    if (!text.trim() || isLoading) return

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    setError(null)

    try {
      const response = await sendMessage(text, currentConvId, language)
      const data = response.data

      if (!currentConvId) {
        setCurrentConvId(data.conversation_id)
        onConversationStart(data.conversation_id)
      }

      const assistantMessage = {
        id: data.message_id,
        role: 'assistant',
        content: data.response,
        model: data.model,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])
      if (viaVoice) {
        try {
          const audioBlob = await textToSpeech(data.response, language)
          const audioUrl = URL.createObjectURL(audioBlob)
          const audio = new Audio(audioUrl)
          audio.play()
        } catch (err) {
          console.error('Voice reply playback failed:', err)
        }
      }
    } catch (err) {
      setError(err.message || 'AURA থেকে response পাওয়া যাচ্ছে না।')
      setMessages(prev => prev.filter(m => m.id !== userMessage.id))
    } finally {
      setIsLoading(false)
    }
  }

  // Ensures a conversation exists before staging a file, since the
  // ingestion endpoint requires a conversation_id.
  const ensureConversationId = async () => {
    if (currentConvId) return currentConvId
    const res = await createConversation('en')
    const newId = res.data.conversation_id
    setCurrentConvId(newId)
    onConversationStart(newId)
    return newId
  }

  const handleFileAttached = fileResult => {
    const fileMessage = {
      id: `file-${Date.now()}`,
      role: 'file',
      filename: fileResult.filename,
      preview: fileResult.preview,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, fileMessage])
  }

  return (
    <div className='chat-window'>
      <div className='chat-window__messages'>
        {loadingHistory && (
          <div className='chat-window__history-loading'>
            <div className='chat-window__thinking-dots'>
              <span />
              <span />
              <span />
            </div>
            <span>Loading conversation...</span>
          </div>
        )}

        {!loadingHistory && messages.length === 0 && !error && (
          <div className='chat-window__empty'>
            <div className='chat-window__empty-icon'>◈</div>
            <h2>AURA কে কিছু জিজ্ঞেস করুন</h2>
            <p>বাংলা, Banglish, বা English — যেকোনো ভাষায় লিখুন।</p>
            <div className='chat-window__suggestions'>
              <button onClick={() => handleSend('তুমি কে?', 'bn')}>
                তুমি কে?
              </button>
              <button
                onClick={() => handleSend('amar jonno ki korte paro?', 'bn')}
              >
                amar jonno ki korte paro?
              </button>
              <button onClick={() => handleSend('What can you do?', 'en')}>
                What can you do?
              </button>
            </div>
          </div>
        )}

        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className='chat-window__thinking'>
            <div className='chat-window__thinking-dots'>
              <span />
              <span />
              <span />
            </div>
            <span>AURA ভাবছে...</span>
          </div>
        )}

        {error && (
          <div className='chat-window__error'>
            <span>⚠️</span>
            <span>{error}</span>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSend={handleSend}
        isLoading={isLoading}
        conversationId={currentConvId}
        ensureConversationId={ensureConversationId}
        onFileAttached={handleFileAttached}
      />
    </div>
  )
}
