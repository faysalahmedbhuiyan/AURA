/**
 * AURA Frontend — Research View.
 *
 * File: src/components/Research/ResearchView.jsx
 * Purpose: Interface for Phase 24 — Autonomous Research Engine.
 *          Search → Review → Confirm → Save workflow.
 */

import { useState } from 'react'
import {
  runResearch,
  quickSearch,
  saveResearch,
  queueResearch
} from '../../services/api'
import './ResearchView.css'

export default function ResearchView () {
  const [query, setQuery] = useState('')
  const [language, setLanguage] = useState('en')
  const [deep, setDeep] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [saveStatus, setSaveStatus] = useState(null)
  const [showSources, setShowSources] = useState(false)

  const handleResearch = async e => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setSaveStatus(null)

    try {
      const res = await runResearch(query.trim(), language, 6, deep)
      setResult(res.data)
    } catch (err) {
      setError(err.message || 'Research failed. Check internet connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!result) return
    setSaveStatus('saving')
    try {
      await saveResearch(
        result.title,
        result.summary,
        result.query,
        result.confidence,
        result.sources,
        result.language
      )
      setSaveStatus('saved')
    } catch (err) {
      setSaveStatus('error')
    }
  }

  const handleQueue = async () => {
    if (!result) return
    setSaveStatus('queuing')
    try {
      await queueResearch(
        result.title,
        result.summary,
        result.query,
        result.language
      )
      setSaveStatus('queued')
    } catch (err) {
      setSaveStatus('error')
    }
  }

  const confColor = score => {
    if (score >= 0.8) return '#4caf7d'
    if (score >= 0.6) return '#f5a623'
    if (score >= 0.4) return '#e67e22'
    return '#e74c3c'
  }

  return (
    <div className='research-view'>
      {/* Search Form */}
      <div className='research-view__form-area'>
        <h2>🔍 Autonomous Research</h2>
        <p>
          AURA searches the internet, ranks sources, and synthesizes
          information.
        </p>

        <form onSubmit={handleResearch} className='research-view__form'>
          <div className='research-view__input-row'>
            <input
              type='text'
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder='Research topic, e.g. "Python async programming" or "বাংলাদেশের অর্থনীতি"'
              disabled={loading}
            />
          </div>

          <div className='research-view__options'>
            <div className='research-view__lang-tabs'>
              {[
                ['en', 'English'],
                ['bn', 'বাংলা']
              ].map(([code, label]) => (
                <button
                  key={code}
                  type='button'
                  className={`research-view__lang-btn ${
                    language === code ? 'research-view__lang-btn--active' : ''
                  }`}
                  onClick={() => setLanguage(code)}
                >
                  {label}
                </button>
              ))}
            </div>

            <label className='research-view__deep-label'>
              <input
                type='checkbox'
                checked={deep}
                onChange={e => setDeep(e.target.checked)}
              />
              Deep Research (slower, more comprehensive)
            </label>

            <button
              type='submit'
              disabled={loading || !query.trim()}
              className='research-view__search-btn'
            >
              {loading ? '⏳ Researching...' : '🔍 Research'}
            </button>
          </div>
        </form>

        {error && <div className='research-view__error'>⚠️ {error}</div>}
      </div>

      {/* Loading */}
      {loading && (
        <div className='research-view__loading'>
          <div className='research-view__loading-steps'>
            <div className='research-view__step research-view__step--active'>
              🔍 Searching...
            </div>
            <div className='research-view__step'>📥 Collecting sources...</div>
            <div className='research-view__step'>
              🏆 Ranking by credibility...
            </div>
            <div className='research-view__step'>
              🧠 Synthesizing with AI...
            </div>
          </div>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className='research-view__result'>
          {/* Header */}
          <div className='research-view__result-header'>
            <h3>{result.title}</h3>
            <div
              className='research-view__confidence'
              style={{ borderColor: confColor(result.confidence) }}
            >
              <span
                className='research-view__conf-score'
                style={{ color: confColor(result.confidence) }}
              >
                {Math.round(result.confidence * 100)}%
              </span>
              <span className='research-view__conf-label'>
                {result.confidence_label}
              </span>
            </div>
          </div>

          {/* Warning */}
          <div className='research-view__warning'>⚠️ {result.warning}</div>

          {/* Summary */}
          <div className='research-view__summary'>
            <h4>📋 Summary</h4>
            <p>{result.summary}</p>
          </div>

          {/* Sources */}
          <div className='research-view__sources'>
            <button
              className='research-view__sources-toggle'
              onClick={() => setShowSources(!showSources)}
            >
              {showSources ? '▼' : '▶'} Sources ({result.sources?.length || 0})
              — {result.successful_sources} fetched from {result.total_sources}{' '}
              found
            </button>

            {showSources &&
              result.sources?.map((source, i) => (
                <div key={i} className='research-view__source'>
                  <div className='research-view__source-header'>
                    <span
                      className={`research-view__source-trust ${
                        source.is_trusted
                          ? 'research-view__source-trust--high'
                          : ''
                      }`}
                    >
                      {source.is_trusted ? '✅ Trusted' : '📄 Source'}
                    </span>
                    <span className='research-view__source-score'>
                      Trust: {Math.round(source.trust_score * 100)}%
                    </span>
                  </div>
                  <div className='research-view__source-title'>
                    {source.title}
                  </div>
                  <a
                    href={source.url}
                    target='_blank'
                    rel='noreferrer'
                    className='research-view__source-url'
                  >
                    🔗 {source.domain} — {source.url.slice(0, 80)}
                  </a>
                  {source.snippet && (
                    <p className='research-view__source-snippet'>
                      {source.snippet}
                    </p>
                  )}
                </div>
              ))}
          </div>

          {/* Action Buttons */}
          <div className='research-view__actions'>
            {!saveStatus && (
              <>
                <button
                  className='research-view__btn research-view__btn--save'
                  onClick={handleSave}
                >
                  ✅ Confirm & Save to Memory
                </button>
                <button
                  className='research-view__btn research-view__btn--queue'
                  onClick={handleQueue}
                >
                  📋 Add to Review Queue
                </button>
                <button
                  className='research-view__btn research-view__btn--discard'
                  onClick={() => setResult(null)}
                >
                  🗑 Discard
                </button>
              </>
            )}

            {saveStatus === 'saving' && (
              <div className='research-view__save-status'>⏳ Saving...</div>
            )}
            {saveStatus === 'saved' && (
              <div className='research-view__save-status research-view__save-status--ok'>
                ✅ Saved to AURA's memory!
              </div>
            )}
            {saveStatus === 'queuing' && (
              <div className='research-view__save-status'>
                ⏳ Adding to queue...
              </div>
            )}
            {saveStatus === 'queued' && (
              <div className='research-view__save-status research-view__save-status--ok'>
                📋 Added to review queue!
              </div>
            )}
            {saveStatus === 'error' && (
              <div className='research-view__save-status research-view__save-status--err'>
                ❌ Save failed. Try again.
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className='research-view__meta'>
            <span>🕐 {new Date(result.timestamp).toLocaleString()}</span>
            <span>📊 {result.total_sources} sources found</span>
            <span>✅ {result.successful_sources} fetched</span>
          </div>
        </div>
      )}
    </div>
  )
}
