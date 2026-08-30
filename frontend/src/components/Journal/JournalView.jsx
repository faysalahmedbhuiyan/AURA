/**
 * AURA Frontend — Journal View.
 *
 * File: src/components/Journal/JournalView.jsx
 * Purpose: Interface for AURA's Development Journal (Phase 12).
 *          Add session logs / decisions / changes, browse history,
 *          and generate a summary for a chosen time window.
 */

import { useState, useEffect } from 'react'
import {
  createJournalEntry,
  listJournalEntries,
  getJournalSummary
} from '../../services/api'
import './JournalView.css'

const CATEGORIES = [
  { id: 'session_log', label: 'Session Log' },
  { id: 'decision', label: 'Decision Record' },
  { id: 'change', label: 'Change' }
]

const CATEGORY_COLOR = {
  session_log: '#6ab7ff',
  decision: '#c98bf5',
  change: '#4caf7d'
}

export default function JournalView () {
  const [tab, setTab] = useState('browse')

  // Form state
  const [category, setCategory] = useState('session_log')
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [tags, setTags] = useState('')
  const [relatedPhase, setRelatedPhase] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)

  // Browse state
  const [entries, setEntries] = useState([])
  const [filterCategory, setFilterCategory] = useState('')
  const [search, setSearch] = useState('')
  const [loadingEntries, setLoadingEntries] = useState(false)

  // Summary state
  const [days, setDays] = useState(7)
  const [summary, setSummary] = useState(null)
  const [loadingSummary, setLoadingSummary] = useState(false)

  const loadEntries = async () => {
    setLoadingEntries(true)
    try {
      const res = await listJournalEntries({
        category: filterCategory || undefined,
        search: search || undefined
      })
      setEntries(res.data)
    } catch (err) {
      console.error('Failed to load journal entries:', err)
    } finally {
      setLoadingEntries(false)
    }
  }

  useEffect(() => {
    if (tab === 'browse') loadEntries()
  }, [tab, filterCategory])

  const handleCreate = async e => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    setSaving(true)
    setSaveError(null)
    try {
      await createJournalEntry({
        category,
        title: title.trim(),
        content: content.trim(),
        tags: tags.trim() || null,
        related_phase: relatedPhase.trim() || null
      })
      setTitle('')
      setContent('')
      setTags('')
      setRelatedPhase('')
      setTab('browse')
      loadEntries()
    } catch (err) {
      setSaveError(err.message || 'Failed to save entry')
    } finally {
      setSaving(false)
    }
  }

  const handleGenerateSummary = async () => {
    setLoadingSummary(true)
    try {
      const res = await getJournalSummary(days)
      setSummary(res.data)
    } catch (err) {
      console.error('Failed to generate summary:', err)
    } finally {
      setLoadingSummary(false)
    }
  }

  return (
    <div className='journal-view'>
      <div className='journal-view__tabs'>
        {['browse', 'new', 'summary'].map(t => (
          <button
            key={t}
            className={`journal-view__tab ${
              tab === t ? 'journal-view__tab--active' : ''
            }`}
            onClick={() => setTab(t)}
          >
            {t === 'browse' ? 'Browse' : t === 'new' ? 'New Entry' : 'Summary'}
          </button>
        ))}
      </div>

      {tab === 'new' && (
        <form onSubmit={handleCreate} className='journal-view__form'>
          <div className='journal-view__category-tabs'>
            {CATEGORIES.map(c => (
              <button
                key={c.id}
                type='button'
                className={`journal-view__category-tab ${
                  category === c.id ? 'journal-view__category-tab--active' : ''
                }`}
                style={
                  category === c.id
                    ? {
                        borderColor: CATEGORY_COLOR[c.id],
                        color: CATEGORY_COLOR[c.id]
                      }
                    : {}
                }
                onClick={() => setCategory(c.id)}
              >
                {c.label}
              </button>
            ))}
          </div>

          <input
            type='text'
            placeholder='Title'
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <textarea
            rows={8}
            placeholder='Content — what happened, what was decided, or what changed...'
            value={content}
            onChange={e => setContent(e.target.value)}
          />
          <div className='journal-view__form-row'>
            <input
              type='text'
              placeholder='Tags (comma separated)'
              value={tags}
              onChange={e => setTags(e.target.value)}
            />
            <input
              type='text'
              placeholder='Related phase (e.g. Phase 12)'
              value={relatedPhase}
              onChange={e => setRelatedPhase(e.target.value)}
            />
          </div>

          {saveError && <div className='journal-view__error'>{saveError}</div>}

          <button
            type='submit'
            disabled={saving || !title.trim() || !content.trim()}
          >
            {saving ? 'Saving...' : 'Save Entry'}
          </button>
        </form>
      )}

      {tab === 'browse' && (
        <div className='journal-view__browse'>
          <div className='journal-view__filters'>
            <select
              value={filterCategory}
              onChange={e => setFilterCategory(e.target.value)}
            >
              <option value=''>All categories</option>
              {CATEGORIES.map(c => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
            <input
              type='text'
              placeholder='Search title/content...'
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadEntries()}
            />
            <button onClick={loadEntries}>Search</button>
          </div>

          {loadingEntries && <p>Loading...</p>}
          {!loadingEntries && entries.length === 0 && (
            <p className='journal-view__empty'>No entries found.</p>
          )}
          {entries.map(entry => (
            <div key={entry.id} className='journal-view__entry'>
              <div className='journal-view__entry-header'>
                <span
                  className='journal-view__category-badge'
                  style={{ background: CATEGORY_COLOR[entry.category] }}
                >
                  {CATEGORIES.find(c => c.id === entry.category)?.label}
                </span>
                <span className='journal-view__entry-title'>{entry.title}</span>
                <span className='journal-view__entry-date'>
                  {new Date(entry.created_at).toLocaleString()}
                </span>
              </div>
              <p className='journal-view__entry-content'>{entry.content}</p>
              {entry.tags && (
                <div className='journal-view__entry-tags'>
                  {entry.tags.split(',').map(t => (
                    <span key={t} className='journal-view__tag'>
                      {t.trim()}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'summary' && (
        <div className='journal-view__summary'>
          <div className='journal-view__summary-controls'>
            <label>Last</label>
            <input
              type='number'
              min='1'
              max='365'
              value={days}
              onChange={e => setDays(parseInt(e.target.value, 10) || 7)}
            />
            <label>days</label>
            <button onClick={handleGenerateSummary} disabled={loadingSummary}>
              {loadingSummary ? 'Generating...' : 'Generate Summary'}
            </button>
          </div>

          {summary && (
            <div className='journal-view__summary-result'>
              <div className='journal-view__summary-stats'>
                <div className='journal-view__stat'>
                  <span className='journal-view__stat-value'>
                    {summary.total_entries}
                  </span>
                  <span className='journal-view__stat-label'>
                    Total Entries
                  </span>
                </div>
                <div className='journal-view__stat'>
                  <span className='journal-view__stat-value'>
                    {summary.files_touched.length}
                  </span>
                  <span className='journal-view__stat-label'>
                    Files Touched
                  </span>
                </div>
              </div>

              {Object.entries(summary.groups).map(([cat, items]) => (
                <div key={cat} className='journal-view__section'>
                  <h3>
                    {CATEGORIES.find(c => c.id === cat)?.label || cat} (
                    {summary.by_category[cat]})
                  </h3>
                  {items.map(item => (
                    <div key={item.id} className='journal-view__summary-item'>
                      <strong>{item.title}</strong>
                      <p>{item.content}</p>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
