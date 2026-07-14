/**
 * AURA Frontend — Chat Input Component.
 *
 * File: src/components/Chat/ChatInput.jsx
 * Purpose: Text + voice input. If the user speaks, the transcript is
 *          sent and AURA's reply is auto-spoken back. If the user
 *          types, the reply stays text-only — matches "voice in ->
 *          voice out, text in -> text out" behavior from Phase 21.
 */

import { useState, useRef } from 'react'
import VoiceButton from '../Voice/VoiceButton'
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

  const handleSubmit = (viaVoice = false) => {
    if (!text.trim() || isLoading) return
    onSend(text.trim(), language, viaVoice)
    setText('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(false)
    }
  }

  const handleVoiceTranscript = transcript => {
    setText(transcript)
    // Send immediately with viaVoice=true so the reply gets auto-spoken.
    onSend(transcript, language, true)
    setText('')
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

        {/* Voice Button */}
        <VoiceButton
          onTranscript={handleVoiceTranscript}
          disabled={isLoading}
        />

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
          onClick={() => handleSubmit(false)}
          disabled={!text.trim() || isLoading}
          title='Send message'
        >
          {isLoading ? '⏳' : '▶'}
        </button>
      </div>
      <p className='chat-input__hint'>
        Enter to send • Shift+Enter for newline • Hold 🎤 to speak
      </p>
    </div>
  )
}
