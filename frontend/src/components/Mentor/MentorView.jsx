/**
 * AURA Frontend — Mentor View.
 *
 * File: src/components/Mentor/MentorView.jsx
 * Purpose: Interface for Coding Mentor Mode (Phase 15) — explain a file,
 *          learn a concept, get educational best-practice suggestions,
 *          or ask a question about the codebase. READ-ONLY end to end.
 */

import { useState } from 'react'
import {
  explainFile,
  teachConcept,
  suggestPractices,
  askMentor
} from '../../services/api'
import './MentorView.css'

const TABS = [
  { id: 'explain', label: 'Explain File' },
  { id: 'concept', label: 'Learn a Concept' },
  { id: 'practices', label: 'Best Practices' },
  { id: 'ask', label: 'Ask a Question' }
]

export default function MentorView () {
  const [tab, setTab] = useState('explain')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [explainPath, setExplainPath] = useState('')
  const [explainResult, setExplainResult] = useState(null)

  const [concept, setConcept] = useState('')
  const [conceptResult, setConceptResult] = useState(null)

  const [practicesPath, setPracticesPath] = useState('')
  const [practicesResult, setPracticesResult] = useState(null)

  const [question, setQuestion] = useState('')
  const [questionFile, setQuestionFile] = useState('')
  const [askResult, setAskResult] = useState(null)

  const run = async (fn, setResult) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fn()
      setResult(res.data)
    } catch (err) {
      setError(err.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className='mentor-view'>
      <div className='mentor-view__notice'>
        Read-only — the mentor explains and teaches, never modifies files.
      </div>

      <div className='mentor-view__tabs'>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`mentor-view__tab ${
              tab === t.id ? 'mentor-view__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className='mentor-view__error'>{error}</div>}

      {tab === 'explain' && (
        <div className='mentor-view__panel'>
          <div className='mentor-view__form'>
            <input
              type='text'
              placeholder='Path to a .py file, e.g. D:/AURA/backend/app/services/ollama_service.py'
              value={explainPath}
              onChange={e => setExplainPath(e.target.value)}
            />
            <button
              disabled={loading || !explainPath.trim()}
              onClick={() =>
                run(() => explainFile(explainPath.trim()), setExplainResult)
              }
            >
              {loading ? 'Explaining...' : 'Explain'}
            </button>
          </div>

          {explainResult && (
            <div className='mentor-view__result'>
              <h3>Structure</h3>
              {explainResult.structure.map((s, i) => (
                <div key={i} className='mentor-view__structure-item'>
                  <span className='mentor-view__structure-type'>{s.type}</span>
                  <span className='mentor-view__structure-name'>{s.name}</span>
                  <span className='mentor-view__structure-lines'>
                    L{s.line_start}-{s.line_end}
                  </span>
                </div>
              ))}
              <h3>Explanation</h3>
              <p className='mentor-view__text'>{explainResult.explanation}</p>
            </div>
          )}
        </div>
      )}

      {tab === 'concept' && (
        <div className='mentor-view__panel'>
          <div className='mentor-view__form'>
            <input
              type='text'
              placeholder='A concept, e.g. "async/await", "dependency injection"'
              value={concept}
              onChange={e => setConcept(e.target.value)}
            />
            <button
              disabled={loading || !concept.trim()}
              onClick={() =>
                run(() => teachConcept(concept.trim()), setConceptResult)
              }
            >
              {loading ? 'Teaching...' : 'Teach Me'}
            </button>
          </div>
          {conceptResult && (
            <div className='mentor-view__result'>
              <p className='mentor-view__text mentor-view__text--pre'>
                {conceptResult.explanation}
              </p>
            </div>
          )}
        </div>
      )}

      {tab === 'practices' && (
        <div className='mentor-view__panel'>
          <div className='mentor-view__form'>
            <input
              type='text'
              placeholder='Path to a .py file'
              value={practicesPath}
              onChange={e => setPracticesPath(e.target.value)}
            />
            <button
              disabled={loading || !practicesPath.trim()}
              onClick={() =>
                run(
                  () => suggestPractices(practicesPath.trim()),
                  setPracticesResult
                )
              }
            >
              {loading ? 'Analyzing...' : 'Suggest'}
            </button>
          </div>
          {practicesResult && (
            <div className='mentor-view__result'>
              {practicesResult.suggestions.length === 0 && (
                <p className='mentor-view__empty'>
                  No issues found — clean file!
                </p>
              )}
              {practicesResult.suggestions.map(s => (
                <div key={s.category} className='mentor-view__practice'>
                  <h4>
                    {s.category.replace(/_/g, ' ')} ({s.occurrences}×)
                  </h4>
                  <p>
                    <strong>Why it matters:</strong> {s.why_it_matters}
                  </p>
                  <p>
                    <strong>How to improve:</strong> {s.how_to_improve}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'ask' && (
        <div className='mentor-view__panel'>
          <div className='mentor-view__form mentor-view__form--column'>
            <input
              type='text'
              placeholder='Optional: path to a file for context'
              value={questionFile}
              onChange={e => setQuestionFile(e.target.value)}
            />
            <textarea
              rows={3}
              placeholder='Ask a question about the codebase...'
              value={question}
              onChange={e => setQuestion(e.target.value)}
            />
            <button
              disabled={loading || !question.trim()}
              onClick={() =>
                run(
                  () => askMentor(question.trim(), questionFile.trim() || null),
                  setAskResult
                )
              }
            >
              {loading ? 'Thinking...' : 'Ask'}
            </button>
          </div>
          {askResult && (
            <div className='mentor-view__result'>
              <p className='mentor-view__text mentor-view__text--pre'>
                {askResult.answer}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
