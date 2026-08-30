import { useState } from 'react'
import './MessageBubble.css'

const BACKEND_ORIGIN = 'http://127.0.0.1:8000'

// ── Content parsers ────────────────────────────────────────────────────────

function parseContent (content) {
  const segments = []
  let remaining = content

  const patterns = [
    { type: 'image', regex: /\[\[IMAGE:(.+?)\]\]/ },
    { type: 'video', regex: /\[\[VIDEO:(.+?)\]\]/ },
    { type: 'pdf', regex: /\[\[PDF:(.+?)\]\]/ },
    { type: 'file', regex: /\[\[FILE:(.+?)\]\]/ },
    { type: 'download', regex: /\[\[DOWNLOAD:(.+?)\|(.+?)\]\]/ }
  ]

  while (remaining.length > 0) {
    let earliest = null
    let earliestIndex = Infinity
    let matchedPattern = null

    for (const p of patterns) {
      const m = remaining.match(p.regex)
      if (m && m.index < earliestIndex) {
        earliest = m
        earliestIndex = m.index
        matchedPattern = p
      }
    }

    if (!earliest) {
      segments.push({ type: 'text', content: remaining })
      break
    }

    if (earliestIndex > 0) {
      segments.push({
        type: 'text',
        content: remaining.slice(0, earliestIndex)
      })
    }

    if (matchedPattern.type === 'download') {
      segments.push({ type: 'download', url: earliest[1], label: earliest[2] })
    } else {
      segments.push({ type: matchedPattern.type, url: earliest[1] })
    }

    remaining = remaining.slice(earliestIndex + earliest[0].length)
  }

  return segments
}

// ── Code block renderer ────────────────────────────────────────────────────

function CodeBlock ({ code, lang }) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className='msg-code'>
      <div className='msg-code__header'>
        <span className='msg-code__lang'>{lang || 'code'}</span>
        <button className='msg-code__copy' onClick={copy}>
          {copied ? '✅ Copied' : '📋 Copy'}
        </button>
      </div>
      <pre className='msg-code__pre'>
        <code>{code}</code>
      </pre>
    </div>
  )
}

// ── Markdown-lite renderer ─────────────────────────────────────────────────

function renderMarkdown (text) {
  const blocks = []
  const lines = text.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Fenced code block
    const fenceMatch = line.match(/^```(\w*)$/)
    if (fenceMatch) {
      const lang = fenceMatch[1]
      const codeLines = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      blocks.push(<CodeBlock key={i} code={codeLines.join('\n')} lang={lang} />)
      i++
      continue
    }

    // Heading
    const h3 = line.match(/^### (.+)/)
    const h2 = line.match(/^## (.+)/)
    const h1 = line.match(/^# (.+)/)
    if (h3) {
      blocks.push(
        <h3 key={i} className='msg-h3'>
          {h3[1]}
        </h3>
      )
      i++
      continue
    }
    if (h2) {
      blocks.push(
        <h2 key={i} className='msg-h2'>
          {h2[1]}
        </h2>
      )
      i++
      continue
    }
    if (h1) {
      blocks.push(
        <h1 key={i} className='msg-h1'>
          {h1[1]}
        </h1>
      )
      i++
      continue
    }

    // Bullet list
    if (line.match(/^[-*] /)) {
      const items = []
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        items.push(<li key={i}>{inlineFormat(lines[i].slice(2))}</li>)
        i++
      }
      blocks.push(
        <ul key={`ul-${i}`} className='msg-ul'>
          {items}
        </ul>
      )
      continue
    }

    // Numbered list
    if (line.match(/^\d+\. /)) {
      const items = []
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        items.push(
          <li key={i}>{inlineFormat(lines[i].replace(/^\d+\. /, ''))}</li>
        )
        i++
      }
      blocks.push(
        <ol key={`ol-${i}`} className='msg-ol'>
          {items}
        </ol>
      )
      continue
    }

    // Horizontal rule
    if (line.match(/^---+$/)) {
      blocks.push(<hr key={i} className='msg-hr' />)
      i++
      continue
    }

    // Empty line
    if (line.trim() === '') {
      i++
      continue
    }

    // Normal paragraph
    blocks.push(
      <p key={i} className='msg-p'>
        {inlineFormat(line)}
      </p>
    )
    i++
  }

  return blocks
}

function inlineFormat (text) {
  // Bold **text**
  // Inline code `code`
  // Links [label](url)
  const parts = []
  const regex = /(\*\*(.+?)\*\*|`(.+?)`|\[(.+?)\]\((.+?)\))/g
  let last = 0
  let m

  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))

    if (m[0].startsWith('**')) {
      parts.push(<strong key={m.index}>{m[2]}</strong>)
    } else if (m[0].startsWith('`')) {
      parts.push(
        <code key={m.index} className='msg-inline-code'>
          {m[3]}
        </code>
      )
    } else if (m[0].startsWith('[')) {
      parts.push(
        <a
          key={m.index}
          href={m[5]}
          target='_blank'
          rel='noreferrer'
          className='msg-link'
        >
          {m[4]}
        </a>
      )
    }
    last = m.index + m[0].length
  }

  if (last < text.length) parts.push(text.slice(last))
  return parts.length ? parts : text
}

// ── Segment renderers ──────────────────────────────────────────────────────

function ImageSegment ({ url }) {
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState(false)
  const src = url.startsWith('http') ? url : `${BACKEND_ORIGIN}${url}`

  if (err)
    return (
      <div className='msg-media-err'>
        ❌ Image load failed —{' '}
        <a href={src} target='_blank' rel='noreferrer'>
          open directly
        </a>
      </div>
    )

  return (
    <div className='msg-image-wrap'>
      {!loaded && <div className='msg-media-loading'>🎨 Loading image...</div>}
      <img
        src={src}
        alt='AI generated'
        className={`msg-image ${loaded ? 'msg-image--visible' : ''}`}
        onLoad={() => setLoaded(true)}
        onError={() => setErr(true)}
      />
      {loaded && (
        <a href={src} download className='msg-image-download'>
          ⬇ Download
        </a>
      )}
    </div>
  )
}

function VideoSegment ({ url }) {
  const src = url.startsWith('http') ? url : `${BACKEND_ORIGIN}${url}`
  return (
    <div className='msg-video-wrap'>
      <video controls className='msg-video' src={src}>
        <a href={src} target='_blank' rel='noreferrer'>
          Download video
        </a>
      </video>
      <a href={src} download className='msg-image-download'>
        ⬇ Download Video
      </a>
    </div>
  )
}

function FileSegment ({ url, label }) {
  const src = url.startsWith('http') ? url : `${BACKEND_ORIGIN}${url}`
  const name = label || url.split('/').pop()
  const ext = name.split('.').pop().toLowerCase()

  const icon =
    {
      pdf: '📄',
      doc: '📝',
      docx: '📝',
      xlsx: '📊',
      xls: '📊',
      csv: '📊',
      txt: '📃',
      py: '🐍',
      js: '📜',
      zip: '🗜',
      mp4: '🎬',
      mp3: '🎵'
    }[ext] || '📎'

  return (
    <div className='msg-file-chip'>
      <span className='msg-file-chip__icon'>{icon}</span>
      <span className='msg-file-chip__name'>{name}</span>
      <a href={src} download className='msg-file-chip__dl'>
        ⬇
      </a>
    </div>
  )
}

// ── Main content renderer ──────────────────────────────────────────────────

function renderContent (content) {
  const segments = parseContent(content)

  return (
    <div className='message__content'>
      {segments.map((seg, idx) => {
        if (seg.type === 'text') {
          return <div key={idx}>{renderMarkdown(seg.content)}</div>
        }
        if (seg.type === 'image') {
          return <ImageSegment key={idx} url={seg.url} />
        }
        if (seg.type === 'video') {
          return <VideoSegment key={idx} url={seg.url} />
        }
        if (seg.type === 'pdf' || seg.type === 'file') {
          return (
            <FileSegment
              key={idx}
              url={seg.url}
              label={seg.url.split('/').pop()}
            />
          )
        }
        if (seg.type === 'download') {
          return <FileSegment key={idx} url={seg.url} label={seg.label} />
        }
        return null
      })}
    </div>
  )
}

// ── MessageBubble component ────────────────────────────────────────────────

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
      <div className='message__avatar'>{isUser ? '👤' : '◈'}</div>
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
