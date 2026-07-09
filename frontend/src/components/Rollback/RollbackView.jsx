/**
 * AURA Frontend — Rollback View.
 *
 * File: src/components/Rollback/RollbackView.jsx
 * Purpose: Interface for Phase 11 — Rollback System.
 *          View commit history, preview rollbacks, create snapshots,
 *          and restore previous project versions safely.
 */

import { useState, useEffect } from 'react'
import {
  getRollbackStatus,
  getRollbackLog,
  previewRollback,
  rollbackToCommit,
  rollbackFiles,
  listSnapshots,
  createSnapshot,
  restoreSnapshot,
  deleteSnapshot
} from '../../services/api'
import './RollbackView.css'

const TABS = [
  { id: 'history', label: '📋 Commit History' },
  { id: 'snapshots', label: '📌 Snapshots' }
]

export default function RollbackView () {
  const [tab, setTab] = useState('history')
  const [gitStatus, setGitStatus] = useState(null)
  const [commits, setCommits] = useState([])
  const [snapshots, setSnapshots] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Preview state
  const [previewRef, setPreviewRef] = useState(null)
  const [preview, setPreview] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Rollback state
  const [rollbackRef, setRollbackRef] = useState(null)
  const [rollbackDesc, setRollbackDesc] = useState('')
  const [rollbackConfirmed, setRollbackConfirmed] = useState(false)
  const [rollbackResult, setRollbackResult] = useState(null)
  const [rollbackLoading, setRollbackLoading] = useState(false)

  // Snapshot creation state
  const [snapName, setSnapName] = useState('')
  const [snapDesc, setSnapDesc] = useState('')
  const [snapPhase, setSnapPhase] = useState('')
  const [snapLoading, setSnapLoading] = useState(false)

  useEffect(() => {
    loadStatus()
    loadLog()
  }, [])

  useEffect(() => {
    if (tab === 'snapshots') loadSnapshots()
  }, [tab])

  const loadStatus = async () => {
    try {
      const res = await getRollbackStatus()
      setGitStatus(res.data)
    } catch (e) {
      console.error('Status load failed:', e)
    }
  }

  const loadLog = async () => {
    setLoading(true)
    try {
      const res = await getRollbackLog(20)
      setCommits(res.data.commits || [])
    } catch (e) {
      setError('Failed to load commit history')
    } finally {
      setLoading(false)
    }
  }

  const loadSnapshots = async () => {
    try {
      const res = await listSnapshots()
      setSnapshots(res.data.snapshots || [])
    } catch (e) {
      console.error('Snapshots load failed:', e)
    }
  }

  const handlePreview = async ref => {
    setPreviewRef(ref)
    setPreview(null)
    setPreviewLoading(true)
    setRollbackResult(null)
    setRollbackConfirmed(false)
    try {
      const res = await previewRollback(ref)
      setPreview(res.data)
    } catch (e) {
      setError(e.message || 'Preview failed')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleRollback = async () => {
    if (!rollbackRef || !rollbackDesc.trim()) return
    setRollbackLoading(true)
    setError(null)
    setRollbackResult(null)
    try {
      const res = await rollbackToCommit(
        rollbackRef,
        rollbackDesc,
        rollbackConfirmed
      )
      setRollbackResult(res.data)
      setRollbackConfirmed(false)
      loadStatus()
      loadLog()
    } catch (e) {
      setError(e.message || 'Rollback failed')
    } finally {
      setRollbackLoading(false)
    }
  }

  const handleCreateSnapshot = async () => {
    if (!snapName.trim() || !gitStatus?.head_commit) return
    setSnapLoading(true)
    try {
      await createSnapshot(snapName, snapDesc, gitStatus.head_commit, snapPhase)
      setSnapName('')
      setSnapDesc('')
      setSnapPhase('')
      await loadSnapshots()
    } catch (e) {
      setError(e.message || 'Snapshot creation failed')
    } finally {
      setSnapLoading(false)
    }
  }

  const handleDeleteSnapshot = async snapId => {
    try {
      await deleteSnapshot(snapId)
      await loadSnapshots()
    } catch (e) {
      setError(e.message || 'Delete failed')
    }
  }

  const handleRestoreSnapshot = async snapId => {
    if (
      !window.confirm(
        'Restore this snapshot? Current state will be backed up first.'
      )
    )
      return
    try {
      const res = await restoreSnapshot(snapId, true)
      setRollbackResult(res.data)
      loadStatus()
      loadLog()
    } catch (e) {
      setError(e.message || 'Restore failed')
    }
  }

  const formatDate = dateStr => {
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return dateStr
    }
  }

  return (
    <div className='rollback-view'>
      {/* Git Status Bar */}
      {gitStatus && (
        <div className='rollback-view__status'>
          <div className='rollback-view__status-item'>
            <span>🌿</span>
            <code>{gitStatus.branch}</code>
          </div>
          <div className='rollback-view__status-item'>
            <span>🔀</span>
            <code>{gitStatus.head_commit}</code>
          </div>
          <div className='rollback-view__status-item'>
            <span
              className={`rollback-view__clean ${
                gitStatus.is_clean
                  ? 'rollback-view__clean--ok'
                  : 'rollback-view__clean--dirty'
              }`}
            >
              {gitStatus.is_clean ? '✅ Clean' : '⚠️ Uncommitted changes'}
            </span>
          </div>
          <div className='rollback-view__status-msg'>
            {gitStatus.head_message}
          </div>
        </div>
      )}

      {error && (
        <div className='rollback-view__error'>
          ⚠️ {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Rollback Result */}
      {rollbackResult && (
        <div
          className={`rollback-view__result ${
            rollbackResult.success
              ? 'rollback-view__result--ok'
              : 'rollback-view__result--fail'
          }`}
        >
          <div className='rollback-view__result-title'>
            {rollbackResult.success
              ? '✅ Rollback Successful'
              : '❌ Rollback Failed'}
          </div>
          <p>{rollbackResult.message || rollbackResult.error}</p>
          {rollbackResult.undo_instructions && (
            <pre className='rollback-view__undo'>
              {rollbackResult.undo_instructions}
            </pre>
          )}
          <button onClick={() => setRollbackResult(null)}>Dismiss</button>
        </div>
      )}

      {/* Tabs */}
      <div className='rollback-view__tabs'>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`rollback-view__tab ${
              tab === t.id ? 'rollback-view__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* History Tab */}
      {tab === 'history' && (
        <div className='rollback-view__panel'>
          {loading && (
            <div className='rollback-view__loading'>Loading history...</div>
          )}
          {commits.map(commit => (
            <div key={commit.hash} className='rollback-view__commit'>
              <div className='rollback-view__commit-header'>
                <code className='rollback-view__hash'>{commit.short_hash}</code>
                <span className='rollback-view__commit-msg'>
                  {commit.message}
                </span>
                <span className='rollback-view__commit-files'>
                  {commit.files_changed} files
                </span>
              </div>
              <div className='rollback-view__commit-meta'>
                <span>{commit.author}</span>
                <span>{formatDate(commit.date)}</span>
              </div>
              <div className='rollback-view__commit-actions'>
                <button
                  className='rollback-view__btn rollback-view__btn--preview'
                  onClick={() => handlePreview(commit.hash)}
                >
                  👁 Preview
                </button>
                <button
                  className='rollback-view__btn rollback-view__btn--rollback'
                  onClick={() => {
                    setRollbackRef(commit.hash)
                    setPreview(null)
                    handlePreview(commit.hash)
                  }}
                >
                  ↩ Rollback
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Snapshots Tab */}
      {tab === 'snapshots' && (
        <div className='rollback-view__panel'>
          {/* Create Snapshot */}
          <div className='rollback-view__snap-create'>
            <h3>Create Snapshot (current HEAD)</h3>
            {gitStatus && (
              <div className='rollback-view__snap-ref'>
                Points to: <code>{gitStatus.head_commit}</code> —{' '}
                {gitStatus.head_message}
              </div>
            )}
            <input
              type='text'
              placeholder='Snapshot name'
              value={snapName}
              onChange={e => setSnapName(e.target.value)}
            />
            <input
              type='text'
              placeholder='Description (optional)'
              value={snapDesc}
              onChange={e => setSnapDesc(e.target.value)}
            />
            <input
              type='text'
              placeholder='Phase label (optional)'
              value={snapPhase}
              onChange={e => setSnapPhase(e.target.value)}
            />
            <button
              onClick={handleCreateSnapshot}
              disabled={snapLoading || !snapName.trim()}
            >
              {snapLoading ? 'Creating...' : '📌 Create Snapshot'}
            </button>
          </div>

          {/* Snapshot List */}
          {snapshots.length === 0 && (
            <div className='rollback-view__empty'>
              No snapshots yet. Create one to mark important milestones.
            </div>
          )}
          {snapshots.map(snap => (
            <div key={snap.snapshot_id} className='rollback-view__snap'>
              <div className='rollback-view__snap-header'>
                <span className='rollback-view__snap-name'>{snap.name}</span>
                {snap.phase && (
                  <span className='rollback-view__snap-phase'>
                    {snap.phase}
                  </span>
                )}
              </div>
              <p className='rollback-view__snap-desc'>{snap.description}</p>
              <div className='rollback-view__snap-meta'>
                <code>{snap.git_ref}</code>
                <span>{formatDate(snap.created_at)}</span>
              </div>
              <div className='rollback-view__snap-actions'>
                <button
                  className='rollback-view__btn rollback-view__btn--restore'
                  onClick={() => handleRestoreSnapshot(snap.snapshot_id)}
                >
                  ↩ Restore
                </button>
                <button
                  className='rollback-view__btn rollback-view__btn--delete'
                  onClick={() => handleDeleteSnapshot(snap.snapshot_id)}
                >
                  🗑 Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview + Rollback Panel */}
      {(preview || previewLoading || rollbackRef) && (
        <div className='rollback-view__preview-panel'>
          {previewLoading && (
            <div className='rollback-view__loading'>Loading preview...</div>
          )}

          {preview && (
            <>
              <div className='rollback-view__preview-header'>
                <h3>
                  Preview: rollback to{' '}
                  <code>{preview.target_ref?.slice(0, 8)}</code>
                </h3>
                {preview.commit && <p>{preview.commit.message}</p>}
              </div>

              {preview.files_that_would_change?.length > 0 && (
                <div className='rollback-view__preview-files'>
                  <h4>
                    Files that would change (
                    {preview.files_that_would_change.length})
                  </h4>
                  {preview.files_that_would_change.map(f => (
                    <code key={f} className='rollback-view__file-tag'>
                      {f}
                    </code>
                  ))}
                </div>
              )}

              {/* Rollback Form */}
              <div className='rollback-view__rollback-form'>
                <input
                  type='text'
                  placeholder='Reason for rollback'
                  value={rollbackDesc}
                  onChange={e => setRollbackDesc(e.target.value)}
                />

                <label className='rollback-view__confirm-label'>
                  <input
                    type='checkbox'
                    checked={rollbackConfirmed}
                    onChange={e => setRollbackConfirmed(e.target.checked)}
                  />
                  I understand this will restore files to commit{' '}
                  <code>{preview.target_ref?.slice(0, 8)}</code>. Current state
                  will be backed up first.
                </label>

                <div className='rollback-view__rollback-actions'>
                  <button
                    className='rollback-view__btn rollback-view__btn--cancel'
                    onClick={() => {
                      setPreview(null)
                      setRollbackRef(null)
                      setRollbackConfirmed(false)
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    className='rollback-view__btn rollback-view__btn--apply'
                    onClick={handleRollback}
                    disabled={
                      !rollbackConfirmed ||
                      !rollbackDesc.trim() ||
                      rollbackLoading
                    }
                  >
                    {rollbackLoading
                      ? '⏳ Rolling back...'
                      : '↩ Apply Rollback'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
