/**
 * AURA Frontend — Chat Window.
 *
 * File: src/components/Chat/ChatWindow.jsx
 * Purpose: Main chat interface — displays messages and handles
 *          text input and voice input for conversation with AURA.
 */

import { useState, useEffect, useRef } from 'react'
import { sendMessage } from '../../services/api'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import './ChatWindow.css'

export default function ChatWindow ({ conversationId, onConversationStart }) {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [currentConvId, setCurrentConvId] = useState(conversationId)
  const messagesEndRef = useRef(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset when new conversation requested
  useEffect(() => {
    if (conversationId === null) {
      setMessages([])
      setCurrentConvId(null)
      setError(null)
    }
  }, [conversationId])

  const handleSend = async (text, language = 'en') => {
    if (!text.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
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

      // Set conversation ID on first message
      if (!currentConvId) {
        setCurrentConvId(data.conversation_id)
        onConversationStart(data.conversation_id)
      }

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        model: data.model,
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError(err.message || 'Failed to get response from AURA.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className='chat-window'>
      {/* Messages Area */}
      <div className='chat-window__messages'>
        {messages.length === 0 && !isLoading && (
          <div className='chat-window__empty'>
            <div className='chat-window__empty-icon'>◈</div>
            <h2>How can I help you?</h2>
            <p>Ask me anything in Bangla, English, Hindi, or Korean.</p>
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
            <span>AURA is thinking...</span>
          </div>
        )}

        {error && (
          <div className='chat-window__error'>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}
