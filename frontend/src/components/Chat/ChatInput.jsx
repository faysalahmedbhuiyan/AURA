/**
 * AURA Frontend — Chat Input Component.
 *
 * File: src/components/Chat/ChatInput.jsx
 * Purpose: Text + voice input, plus file attach (PDF/DOCX/image).
 *          Attaching a file stages it server-side and shows a bubble
 *          in chat; the next typed/spoken message becomes an
 *          instruction about that file.
 */

import { useState, useRef } from 'react'
import VoiceButton from '../Voice/VoiceButton'
import { stageFile } from '../../services/api'
import './ChatInput.css'

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'bn', label: 'বাং' },
  { code: 'hi', label: 'हिं' },
  { code: 'ko', label: '한' }
]

export default function ChatInput ({
  onSend,
  isLoading,
  conversationId,
  ensureConversationId,
  onFileAttached
}) {
  const [text, setText] = useState('')
  const [language, setLanguage] = useState('en')
  const [ingesting, setIngesting] = useState(false)
  const [ingestError, setIngestError] = useState(null)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)

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
    onSend(transcript, language, true)
    setText('')
  }

  const handleFileSelected = async e => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''

    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'docx', 'png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
      setIngestError('শুধু PDF, DOCX, PNG, JPG সাপোর্ট করে।')
      return
    }

    setIngesting(true)
    setIngestError(null)
    try {
      const convId = await ensureConversationId()
      const result = await stageFile(file, convId, language)
      onFileAttached(result)
    } catch (err) {
      setIngestError(err.response?.data?.detail || 'ফাইল প্রসেস করা যায়নি।')
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className='chat-input'>
      <div className='chat-input__container'>
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

        {/* Attach File */}
        <input
          ref={fileInputRef}
          type='file'
          accept='.pdf,.docx,.png,.jpg,.jpeg,.webp'
          style={{ display: 'none' }}
          onChange={handleFileSelected}
        />
        <button
          type='button'
          className='chat-input__attach'
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading || ingesting}
          title='PDF/DOCX/ছবি সংযুক্ত করুন'
        >
          {ingesting ? '⏳' : '📎'}
        </button>

        <VoiceButton
          onTranscript={handleVoiceTranscript}
          disabled={isLoading}
          language={language}
        />

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
        Enter to send • Shift+Enter for newline • Hold 🎤 to speak • 📎 to
        attach
      </p>
      {ingestError && (
        <p className='chat-input__ingest-notice'>{ingestError}</p>
      )}
    </div>
  )
}
