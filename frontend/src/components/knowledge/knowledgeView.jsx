/**
 * AURA Frontend — Knowledge View.
 *
 * File: src/components/Knowledge/KnowledgeView.jsx
 * Purpose: Lets the user research a topic from the web, review the
 *          AI-generated candidate, and confirm it into permanent memory.
 *          Enforces AURA's confirm-before-save rule end to end:
 *          Research (read-only) → Add as pending → Confirm.
 */

import { useState, useEffect } from 'react'
import {
  researchTopic,
  addKnowledge,
  confirmKnowledge,
  getPendingKnowledge,
  getConfirmedKnowledge
} from '../../services/api'
import './KnowledgeView.css'

const TABS = [
  { id: 'research', label: 'Research' },
  { id: 'pending', label: 'Pending Review' },
  { id: 'confirmed', label: 'Confirmed' }
]

export default function KnowledgeView () {
  const [tab, setTab] = useState('research')

  // Research state
  const [query, setQuery] = useState('')
  const [researching, setResearching] = useState(false)
  const [candidate, setCandidate] = useState(null)
  const [error, setError] = useState(null)

  // Pending / Confirmed lists
  const [pending, setPending] = useState([])
  const [confirmed, setConfirmed] = useState([])
  const [listLoading, setListLoading] = useState(false)

  const loadLists = async () => {
    setListLoading(true)
    try {
      const [pendingRes, confirmedRes] = await Promise.all([
        getPendingKnowledge(),
        getConfirmedKnowledge()
      ])
      setPending(pendingRes.data)
      setConfirmed(confirmedRes.data)
    } catch (err) {
      console.error('Failed to load knowledge lists:', err)
    } finally {
      setListLoading(false)
    }
  }

  useEffect(() => {
    if (tab === 'pending' || tab === 'confirmed') {
      loadLists()
    }
  }, [tab])

  const handleResearch = async e => {
    e.preventDefault()
    if (!query.trim()) return
    setResearching(true)
    setError(null)
    setCandidate(null)
    try {
      const res = await researchTopic(query.trim())
      setCandidate(res.data)
    } catch (err) {
      setError(err.message || 'Research failed')
    } finally {
      setResearching(false)
    }
  }

  const updateCandidateField = (field, value) => {
    setCandidate(prev => ({ ...prev, [field]: value }))
  }

  const handleSaveAsPending = async () => {
    if (!candidate) return
    try {
      const sourceUrls = candidate.sources.map(s => s.url).join(', ')
      const primarySource = candidate.sources[0]
      await addKnowledge({
        title: candidate.title,
        summary: candidate.summary,
        source_url: primarySource?.url || null,
        source_name: primarySource?.name || null,
        category: null,
        tags: null,
        confidence: candidate.suggested_confidence,
        language: candidate.language
      })
      setCandidate(null)
      setQuery('')
      setTab('pending')
    } catch (err) {
      setError(err.message || 'Failed to save as pending')
    }
  }

  const handleConfirm = async entryId => {
    try {
      await confirmKnowledge(entryId)
      await loadLists()
    } catch (err) {
      console.error('Failed to confirm entry:', err)
    }
  }

  return (
    <div className='knowledge-view'>
      <div className='knowledge-view__tabs'>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`knowledge-view__tab ${
              tab === t.id ? 'knowledge-view__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'research' && (
        <div className='knowledge-view__panel'>
          <form onSubmit={handleResearch} className='knowledge-view__search'>
            <input
              type='text'
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder='What should AURA research? e.g. "quantum computing basics"'
              disabled={researching}
            />
            <button type='submit' disabled={researching || !query.trim()}>
              {researching ? 'Researching...' : 'Research'}
            </button>
          </form>

          {error && <div className='knowledge-view__error'>{error}</div>}

          {candidate && (
            <div className='knowledge-view__candidate'>
              <div className='knowledge-view__candidate-notice'>
                This is a draft from the web — nothing is saved yet. Review and
                edit before confirming.
              </div>

              <label>Title</label>
              <input
                type='text'
                value={candidate.title}
                onChange={e => updateCandidateField('title', e.target.value)}
              />

              <label>Summary</label>
              <textarea
                rows={8}
                value={candidate.summary}
                onChange={e => updateCandidateField('summary', e.target.value)}
              />

              <label>
                Confidence: {Math.round(candidate.suggested_confidence * 100)}%
              </label>
              <input
                type='range'
                min='0'
                max='1'
                step='0.05'
                value={candidate.suggested_confidence}
                onChange={e =>
                  updateCandidateField(
                    'suggested_confidence',
                    parseFloat(e.target.value)
                  )
                }
              />

              {candidate.sources.length > 0 && (
                <div className='knowledge-view__sources'>
                  <label>Sources</label>
                  <ul>
                    {candidate.sources.map(s => (
                      <li key={s.url}>
                        <a href={s.url} target='_blank' rel='noreferrer'>
                          {s.name}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className='knowledge-view__candidate-actions'>
                <button
                  className='knowledge-view__discard'
                  onClick={() => setCandidate(null)}
                >
                  Discard
                </button>
                <button
                  className='knowledge-view__save'
                  onClick={handleSaveAsPending}
                >
                  Save as Pending
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'pending' && (
        <div className='knowledge-view__panel'>
          {listLoading && <p>Loading...</p>}
          {!listLoading && pending.length === 0 && (
            <p className='knowledge-view__empty'>
              No pending entries. Research a topic to add one.
            </p>
          )}
          {pending.map(entry => (
            <div key={entry.id} className='knowledge-view__entry'>
              <h4>{entry.title}</h4>
              <p>{entry.summary}</p>
              <div className='knowledge-view__entry-meta'>
                <span>{entry.source_name || 'No source'}</span>
                <span>{Math.round(entry.confidence * 100)}% confidence</span>
              </div>
              <button
                className='knowledge-view__confirm'
                onClick={() => handleConfirm(entry.id)}
              >
                Confirm & Save Permanently
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === 'confirmed' && (
        <div className='knowledge-view__panel'>
          {listLoading && <p>Loading...</p>}
          {!listLoading && confirmed.length === 0 && (
            <p className='knowledge-view__empty'>No confirmed knowledge yet.</p>
          )}
          {confirmed.map(entry => (
            <div key={entry.id} className='knowledge-view__entry'>
              <h4>{entry.title}</h4>
              <p>{entry.summary}</p>
              <div className='knowledge-view__entry-meta'>
                <span>{entry.source_name || 'No source'}</span>
                <span>{Math.round(entry.confidence * 100)}% confidence</span>
                <span>{entry.is_indexed ? '✓ Indexed' : 'Not indexed'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
