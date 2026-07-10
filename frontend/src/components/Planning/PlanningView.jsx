/**
 * AURA Frontend — Planning View.
 *
 * File: src/components/Planning/PlanningView.jsx
 * Purpose: Interface for AURA's Self Improvement Planner (Phase 9) and
 *          Safe Self Modification (Phase 10). Lets the user describe a
 *          desired change, review the plan (affected files, risk), load
 *          a file's current content, edit it, and apply the change with
 *          an automatic backup and one-click undo.
 */

import { useState } from 'react'
import {
  createPlan,
  applyChange,
  rollbackChange,
  executeAgent
} from '../../services/api'
import './PlanningView.css'

export default function PlanningView () {
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [plan, setPlan] = useState(null)

  const [applyTarget, setApplyTarget] = useState('')
  const [newContent, setNewContent] = useState('')
  const [applying, setApplying] = useState(false)
  const [applyResult, setApplyResult] = useState(null)
  const [loadingContent, setLoadingContent] = useState(false)
  const [loadContentError, setLoadContentError] = useState(null)

  const resetApplyState = () => {
    setApplyTarget('')
    setNewContent('')
    setApplyResult(null)
    setLoadContentError(null)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    if (!description.trim()) return
    setLoading(true)
    setError(null)
    setPlan(null)
    resetApplyState()
    try {
      const res = await createPlan(description.trim())
      setPlan(res.data)
    } catch (err) {
      setError(err.message || 'Planning failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectFile = e => {
    // Clear any stale content/result from a previously selected file —
    // prevents accidentally writing one file's content into another.
    setApplyTarget(e.target.value)
    setNewContent('')
    setApplyResult(null)
    setLoadContentError(null)
  }

  const handleLoadCurrentContent = async () => {
    if (!applyTarget) return
    setLoadingContent(true)
    setLoadContentError(null)
    try {
      const res = await executeAgent('file', 'read', { path: applyTarget })
      if (res.data.success) {
        setNewContent(res.data.data.content)
      } else {
        setLoadContentError(res.data.error || 'Could not read file.')
      }
    } catch (err) {
      setLoadContentError(err.message || 'Could not read file.')
    } finally {
      setLoadingContent(false)
    }
  }

  const handleApply = async () => {
    if (!applyTarget || !newContent.trim()) return
    const doubleCheck = window.confirm(
      `This will overwrite:\n${applyTarget}\n\nA backup will be created automatically. Continue?`
    )
    if (!doubleCheck) return

    setApplying(true)
    setApplyResult(null)
    try {
      const res = await applyChange(
        applyTarget,
        newContent,
        true,
        'Manual edit via Planning view'
      )
      setApplyResult(res.data)
    } catch (err) {
      setApplyResult({ success: false, error: err.message })
    } finally {
      setApplying(false)
    }
  }

  const handleRollback = async backupPath => {
    try {
      await rollbackChange(backupPath)
      setApplyResult(prev => ({ ...prev, rolledBack: true }))
    } catch (err) {
      console.error('Rollback failed:', err)
    }
  }

  const riskColor = level =>
    ({
      low: '#4caf7d',
      medium: '#f5a623',
      high: '#e67e22',
      critical: '#e74c3c'
    }[level] || '#888')

  return (
    <div className='planning-view'>
      <div className='planning-view__notice'>
        Every change requires your explicit confirmation and is backed up
        automatically before it's written — nothing is applied silently.
      </div>

      <form onSubmit={handleSubmit} className='planning-view__form'>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder='Describe what you want improved or changed, e.g. "add retry logic to ollama_service.py" or "make the sidebar buttons rounder"'
          rows={4}
          disabled={loading}
        />
        <button type='submit' disabled={loading || !description.trim()}>
          {loading ? 'Planning...' : 'Create Plan'}
        </button>
      </form>

      {error && <div className='planning-view__error'>{error}</div>}

      {plan && (
        <>
          <div className='planning-view__result'>
            <div className='planning-view__risk'>
              <span
                className='planning-view__risk-badge'
                style={{ background: riskColor(plan.risk.level) }}
              >
                {plan.risk.level.toUpperCase()} RISK
              </span>
              <p>{plan.risk.explanation}</p>
            </div>

            <div className='planning-view__section'>
              <h3>Why this risk level</h3>
              <ul>
                {plan.risk.factors.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>

            <div className='planning-view__section'>
              <h3>
                Affected Files ({plan.affected_files.length})
                {plan.analysis.likely_scope !== 'full' && (
                  <span className='planning-view__scope-tag'>
                    {plan.analysis.likely_scope}
                  </span>
                )}
              </h3>
              {plan.affected_files.length === 0 && (
                <p className='planning-view__empty'>
                  No confident matches found — try mentioning a specific
                  filename or clearer keywords.
                </p>
              )}
              {plan.affected_files.map(f => (
                <div key={f.path} className='planning-view__file'>
                  <div className='planning-view__file-header'>
                    <span className='planning-view__file-path'>
                      {f.path.split(/[\\/]/).pop()}
                    </span>
                    <span className='planning-view__relevance'>
                      {Math.round(f.relevance * 100)}% match
                    </span>
                  </div>
                  <p className='planning-view__reason'>{f.reason}</p>
                </div>
              ))}
            </div>

            <div className='planning-view__approval'>{plan.approval_note}</div>
          </div>

          {plan.affected_files.length > 0 && (
            <div className='planning-view__section'>
              <h3>Apply a Change</h3>
              <p className='planning-view__apply-warning'>
                Select a file, load its current content (recommended before
                editing), then write the full new content and confirm. A backup
                is created automatically before writing.
              </p>
              <select
                className='planning-view__file-select'
                value={applyTarget}
                onChange={handleSelectFile}
              >
                <option value=''>-- Select a file to edit --</option>
                {plan.affected_files.map(f => (
                  <option key={f.path} value={f.path}>
                    {f.path}
                  </option>
                ))}
              </select>

              {applyTarget && (
                <>
                  <button
                    className='planning-view__load-btn'
                    onClick={handleLoadCurrentContent}
                    disabled={loadingContent}
                    type='button'
                  >
                    {loadingContent ? 'Loading...' : 'Load Current Content'}
                  </button>

                  {loadContentError && (
                    <div className='planning-view__error'>
                      {loadContentError}
                    </div>
                  )}

                  <textarea
                    className='planning-view__content-editor'
                    rows={12}
                    value={newContent}
                    onChange={e => setNewContent(e.target.value)}
                    placeholder='Load the current content above, or write the FULL new content for this file...'
                  />
                  <button
                    className='planning-view__apply-btn'
                    onClick={handleApply}
                    disabled={applying || !newContent.trim()}
                    type='button'
                  >
                    {applying ? 'Applying...' : 'Apply Change (with backup)'}
                  </button>
                </>
              )}

              {applyResult && (
                <div
                  className={`planning-view__apply-result ${
                    applyResult.success
                      ? 'planning-view__apply-result--success'
                      : 'planning-view__apply-result--fail'
                  }`}
                >
                  {applyResult.success ? (
                    <>
                      <p>✓ Applied successfully.</p>
                      <p className='planning-view__commit-msg'>
                        Suggested commit: {applyResult.suggested_commit_message}
                      </p>
                      {applyResult.rolledBack ? (
                        <p>✓ Rolled back.</p>
                      ) : (
                        <button
                          className='planning-view__rollback-btn'
                          onClick={() =>
                            handleRollback(applyResult.backup.backup_path)
                          }
                          type='button'
                        >
                          Undo this change
                        </button>
                      )}
                    </>
                  ) : (
                    <p>✗ {applyResult.error}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
