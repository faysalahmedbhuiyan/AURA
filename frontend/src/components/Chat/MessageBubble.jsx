/**
 * AURA Frontend — Message Bubble Component.
 *
 * File: src/components/Chat/MessageBubble.jsx
 * Purpose: Renders a single chat message with proper styling
 *          for user vs assistant messages.
 */

import './MessageBubble.css'

const IMAGE_MARKER = /\[\[IMAGE:(.+?)\]\]/
const BACKEND_ORIGIN = 'http://127.0.0.1:8000'

function renderContent (content) {
  const match = content.match(IMAGE_MARKER)
  if (!match) return <div className='message__content'>{content}</div>

  const before = content.slice(0, match.index).trim()
  const after = content.slice(match.index + match[0].length).trim()

  return (
    <div className='message__content'>
      {before && <p>{before}</p>}
      <img
        src={`${BACKEND_ORIGIN}${match[1]}`}
        alt='attached page'
        className='message__page-image'
      />
      {after && <p>{after}</p>}
    </div>
  )
}

export default function MessageBubble ({ message }) {
  const isUser = message.role === 'user'
  const isFile = message.role === 'file'
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })

  if (isFile) {
    return (
      <div className='message message--file'>
        <div className='message__avatar'>📎</div>
        <div className='message__body'>
          <div className='message__header'>
            <span className='message__sender'>Attached</span>
            <span className='message__time'>{time}</span>
          </div>
          <div className='message__content'>
            <strong>{message.filename}</strong>
            {message.preview && (
              <div className='message__file-preview'>{message.preview}</div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`message ${isUser ? 'message--user' : 'message--assistant'}`}
    >
      {/* Avatar */}
      <div className='message__avatar'>{isUser ? '👤' : '◈'}</div>

      {/* Content */}
      <div className='message__body'>
        <div className='message__header'>
          <span className='message__sender'>{isUser ? 'You' : 'AURA'}</span>
          <span className='message__time'>{time}</span>
        </div>
        {renderContent(message.content)}
        {message.model && <div className='message__model'>{message.model}</div>}
      </div>
    </div>
  )
}
