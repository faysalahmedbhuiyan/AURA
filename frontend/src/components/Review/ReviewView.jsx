/**
 * AURA Frontend — Review View.
 *
 * File: src/components/Review/ReviewView.jsx
 * Purpose: Interface for AURA's Self Review Engine (Phase 8).
 *          READ-ONLY analysis — displays debt score, suggestions,
 *          and per-file issues. Never modifies any file.
 */

import { useState } from 'react'
import { analyzeCode } from '../../services/api'
import './ReviewView.css'

const DEFAULT_PATH = 'D:/AURA/backend/app'

export default function ReviewView () {
  const [path, setPath] = useState(DEFAULT_PATH)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)
  const [expandedFile, setExpandedFile] = useState(null)

  const handleAnalyze = async e => {
    e.preventDefault()
    if (!path.trim()) return
    setLoading(true)
    setError(null)
    setReport(null)
    try {
      const res = await analyzeCode(path.trim())
      setReport(res.data)
    } catch (err) {
      setError(err.message || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = score => {
    if (score === 0) return '#4caf7d'
    if (score < 10) return '#f5a623'
    return '#e74c3c'
  }

  const priorityColor = priority =>
    ({
      high: '#e74c3c',
      medium: '#f5a623',
      low: '#6ab7ff'
    }[priority] || '#888')

  return (
    <div className='review-view'>
      <div className='review-view__notice'>
        Read-only analysis — AURA never modifies files during review.
      </div>

      <form onSubmit={handleAnalyze} className='review-view__search'>
        <input
          type='text'
          value={path}
          onChange={e => setPath(e.target.value)}
          placeholder='Path to analyze, e.g. D:/AURA/backend/app'
          disabled={loading}
        />
        <button type='submit' disabled={loading || !path.trim()}>
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </form>

      {error && <div className='review-view__error'>{error}</div>}

      {report && (
        <>
          <div className='review-view__summary'>
            <div className='review-view__stat'>
              <span className='review-view__stat-value'>
                {report.files_analyzed}
              </span>
              <span className='review-view__stat-label'>Files Analyzed</span>
            </div>
            <div className='review-view__stat'>
              <span className='review-view__stat-value'>
                {report.debt_summary.total_issues}
              </span>
              <span className='review-view__stat-label'>Total Issues</span>
            </div>
            <div className='review-view__stat'>
              <span className='review-view__stat-value'>
                {report.debt_summary.average_score}
              </span>
              <span className='review-view__stat-label'>Avg Debt Score</span>
            </div>
          </div>

          <div className='review-view__section'>
            <h3>Suggestions</h3>
            {report.suggestions.map(s => (
              <div key={s.title} className='review-view__suggestion'>
                <div className='review-view__suggestion-header'>
                  <span
                    className='review-view__priority-dot'
                    style={{ background: priorityColor(s.priority) }}
                  />
                  <strong>{s.title}</strong>
                </div>
                <p>{s.description}</p>
                <div className='review-view__affected'>
                  {s.affected_files.length} file(s) affected
                </div>
              </div>
            ))}
          </div>

          <div className='review-view__section'>
            <h3>Worst Files</h3>
            {report.debt_summary.worst_files.map(f => (
              <div key={f.file} className='review-view__file-row'>
                <span
                  className='review-view__score-badge'
                  style={{ background: scoreColor(f.score) }}
                >
                  {f.score}
                </span>
                <button
                  className='review-view__file-name'
                  onClick={() =>
                    setExpandedFile(expandedFile === f.file ? null : f.file)
                  }
                >
                  {f.file.split('\\').pop()}
                </button>
                <span className='review-view__issue-count'>
                  {f.issue_count} issue(s)
                </span>
              </div>
            ))}
          </div>

          {expandedFile && (
            <div className='review-view__section'>
              <h3>Issues in {expandedFile.split('\\').pop()}</h3>
              {report.issues
                .filter(i => i.file_path === expandedFile)
                .map((issue, idx) => (
                  <div key={idx} className='review-view__issue'>
                    <span
                      className='review-view__priority-dot'
                      style={{ background: priorityColor(issue.severity) }}
                    />
                    <span className='review-view__issue-line'>
                      L{issue.line}
                    </span>
                    <span className='review-view__issue-message'>
                      {issue.message}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
