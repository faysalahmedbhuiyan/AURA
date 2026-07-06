/**
 * AURA Frontend — Chat Input Component.
 *
 * File: src/components/Chat/ChatInput.jsx
 * Purpose: Text input with send button and language selector.
 *          Supports Enter to send, Shift+Enter for newline.
 */

import { useState, useRef } from 'react'
import './ChatInput.css'

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'bn', label: 'বাং' },
  { code: 'hi', label: 'हिं' },
  { code: 'ko', label: '한' }
]

export default function ChatInput ({ onSend, isLoading }) {
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('en')
  const textareaRef = useRef(null)

  const handleSubmit = () => {
    if (!text.trim() || isLoading) return
    onSend(text.trim(), language)
    setText('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className='chat-input'>
      <div className='chat-input__container'>
        {/* Language Selector */}
        <div className='chat-input__languages'>
          {LANGUAGES.map(lang => (
            <button
              key={lang.code}
              className={`chat-input__lang ${
                language === lang.code ? 'chat-input__lang--active' : ''
              }`}
              onClick={() => setLanguage(lang.code)}
              title={lang.code}
            >
              {lang.label}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          className='chat-input__textarea'
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Message AURA... (Enter to send, Shift+Enter for newline)'
          rows={1}
          disabled={isLoading}
        />

        {/* Send Button */}
        <button
          className='chat-input__send'
          onClick={handleSubmit}
          disabled={!text.trim() || isLoading}
          title='Send message'
        >
          {isLoading ? '⏳' : '▶'}
        </button>
      </div>
      <p className='chat-input__hint'>
        Enter to send • Shift+Enter for newline
      </p>
    </div>
  )
}
