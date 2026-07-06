/**
 * AURA Frontend — Message Bubble Component.
 *
 * File: src/components/Chat/MessageBubble.jsx
 * Purpose: Renders a single chat message with proper styling
 *          for user vs assistant messages.
 */

import './MessageBubble.css'

export default function MessageBubble ({ message }) {
  const isUser = message.role === 'user'
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })

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
        <div className='message__content'>{message.content}</div>
        {message.model && <div className='message__model'>{message.model}</div>}
      </div>
    </div>
  )
}
