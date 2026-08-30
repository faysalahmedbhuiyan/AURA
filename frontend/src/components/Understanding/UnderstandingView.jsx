/**
 * AURA Frontend — Understanding View.
 *
 * File: src/components/Understanding/UnderstandingView.jsx
 * Purpose: Interface for Phase 14 — Project Understanding Engine.
 *          Browse project structure, dependency graph, search code,
 *          and discover API routes.
 */

import { useState, useEffect } from 'react'
import {
  getProjectSummary,
  getProjectStructure,
  getDependencies,
  searchCode,
  getApiRoutes,
  findFunctionDef,
  findClassDef
} from '../../services/api'
import './UnderstandingView.css'

const TABS = [
  { id: 'summary', label: '📊 Summary' },
  { id: 'structure', label: '🗂 Structure' },
  { id: 'deps', label: '🔗 Dependencies' },
  { id: 'search', label: '🔍 Search' },
  { id: 'routes', label: '🛣 API Routes' }
]

export default function UnderstandingView () {
  const [tab, setTab] = useState('summary')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [summary, setSummary] = useState(null)
  const [structure, setStructure] = useState(null)
  const [expandedFolders, setExpandedFolders] = useState(new Set(['.']))
  const [deps, setDeps] = useState(null)
  const [selectedModule, setSelectedModule] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchRegex, setSearchRegex] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [routes, setRoutes] = useState(null)

  // Quick search shortcuts
  const [quickType, setQuickType] = useState('keyword') // keyword | function | class
  const [quickQuery, setQuickQuery] = useState('')

  useEffect(() => {
    if (tab === 'summary' && !summary) loadSummary()
    if (tab === 'structure' && !structure) loadStructure()
    if (tab === 'deps' && !deps) loadDeps()
    if (tab === 'routes' && !routes) loadRoutes()
  }, [tab])

  const loadSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getProjectSummary()
      setSummary(res.data)
    } catch (e) {
      setError('Failed to load summary')
    } finally {
      setLoading(false)
    }
  }

  const loadStructure = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getProjectStructure(5)
      setStructure(res.data)
    } catch (e) {
      setError('Failed to load structure')
    } finally {
      setLoading(false)
    }
  }

  const loadDeps = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getDependencies()
      setDeps(res.data)
    } catch (e) {
      setError('Failed to load dependencies')
    } finally {
      setLoading(false)
    }
  }

  const loadRoutes = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getApiRoutes()
      setRoutes(res.data)
    } catch (e) {
      setError('Failed to load routes')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async e => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setSearchLoading(true)
    setError(null)
    try {
      const res = await searchCode(searchQuery, searchRegex)
      setSearchResults(res.data)
    } catch (e) {
      setError(e.message || 'Search failed')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleQuickSearch = async e => {
    e.preventDefault()
    if (!quickQuery.trim()) return
    setSearchLoading(true)
    setError(null)
    setSearchResults(null)
    try {
      let res
      if (quickType === 'function') {
        res = await findFunctionDef(quickQuery.trim())
      } else if (quickType === 'class') {
        res = await findClassDef(quickQuery.trim())
      } else {
        res = await searchCode(quickQuery.trim(), false)
      }
      setSearchResults(res.data)
    } catch (e) {
      setError(e.message || 'Quick search failed')
    } finally {
      setSearchLoading(false)
    }
  }

  const toggleFolder = path => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const humanSize = bytes => {
    if (!bytes) return '0B'
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`
  }

  return (
    <div className='understanding-view'>
      <div className='understanding-view__tabs'>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`understanding-view__tab ${
              tab === t.id ? 'understanding-view__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className='understanding-view__error'>
          ⚠️ {error}
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className='understanding-view__panel'>
        {loading && (
          <div className='understanding-view__loading'>Analyzing...</div>
        )}

        {/* ── Summary Tab ─────────────────────────────────────────── */}
        {tab === 'summary' && summary && (
          <div className='understanding-view__summary'>
            <div className='understanding-view__metrics'>
              <div className='understanding-view__metric'>
                <span className='understanding-view__metric-value'>
                  {summary.structure?.total_files ?? '—'}
                </span>
                <span className='understanding-view__metric-label'>
                  Total Files
                </span>
              </div>
              <div className='understanding-view__metric'>
                <span className='understanding-view__metric-value'>
                  {summary.structure?.total_size_human ?? '—'}
                </span>
                <span className='understanding-view__metric-label'>
                  Project Size
                </span>
              </div>
              <div className='understanding-view__metric'>
                <span className='understanding-view__metric-value'>
                  {summary.api?.total_routes ?? '—'}
                </span>
                <span className='understanding-view__metric-label'>
                  API Routes
                </span>
              </div>
              <div className='understanding-view__metric'>
                <span className='understanding-view__metric-value'>
                  {summary.dependencies?.total_python_modules ?? '—'}
                </span>
                <span className='understanding-view__metric-label'>
                  Python Modules
                </span>
              </div>
            </div>

            {summary.structure?.file_types && (
              <div className='understanding-view__section'>
                <h3>File Types</h3>
                <div className='understanding-view__type-grid'>
                  {Object.entries(summary.structure.file_types)
                    .sort(([, a], [, b]) => b - a)
                    .map(([type, count]) => (
                      <div key={type} className='understanding-view__type-item'>
                        <span className='understanding-view__type-name'>
                          {type}
                        </span>
                        <span className='understanding-view__type-count'>
                          {count}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {summary.dependencies?.most_imported?.length > 0 && (
              <div className='understanding-view__section'>
                <h3>Most Imported Modules</h3>
                {summary.dependencies.most_imported.map(m => (
                  <div key={m.module} className='understanding-view__dep-item'>
                    <code>{m.module.replace('app.', '')}</code>
                    <span>{m.imported_by_count} importers</span>
                  </div>
                ))}
              </div>
            )}

            {summary.structure?.largest_files?.length > 0 && (
              <div className='understanding-view__section'>
                <h3>Largest Files</h3>
                {summary.structure.largest_files.map(f => (
                  <div
                    key={f.relative_path}
                    className='understanding-view__file-item'
                  >
                    <code>{f.relative_path}</code>
                    <span>{humanSize(f.size_bytes)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Structure Tab ─────────────────────────────────────────── */}
        {tab === 'structure' && structure && (
          <div className='understanding-view__structure'>
            <div className='understanding-view__struct-summary'>
              {structure.total_files} files • {structure.total_size_human} •{' '}
              {structure.folder_count} folders
            </div>
            {structure.folders
              ?.filter(f => f.relative_path === '.')
              .map(folder => (
                <div key={folder.path}>
                  {folder.subfolders.map(sub => {
                    const subFolder = structure.folders?.find(
                      f => f.name === sub && !f.relative_path.includes('/')
                    )
                    return (
                      <div key={sub} className='understanding-view__folder'>
                        <button
                          className='understanding-view__folder-toggle'
                          onClick={() => toggleFolder(sub)}
                        >
                          {expandedFolders.has(sub) ? '▼' : '▶'} 📁 {sub}
                          {subFolder && (
                            <span className='understanding-view__folder-meta'>
                              {subFolder.file_count} files
                            </span>
                          )}
                        </button>
                        {expandedFolders.has(sub) && subFolder && (
                          <div className='understanding-view__folder-files'>
                            {subFolder.files.slice(0, 30).map(f => (
                              <div
                                key={f.path}
                                className='understanding-view__file'
                              >
                                <span className='understanding-view__file-icon'>
                                  {f.file_type === 'python'
                                    ? '🐍'
                                    : f.file_type === 'react'
                                    ? '⚛️'
                                    : f.file_type === 'markdown'
                                    ? '📝'
                                    : f.file_type === 'stylesheet'
                                    ? '🎨'
                                    : '📄'}
                                </span>
                                <span className='understanding-view__file-name'>
                                  {f.name}
                                </span>
                                <span className='understanding-view__file-size'>
                                  {humanSize(f.size_bytes)}
                                </span>
                              </div>
                            ))}
                            {subFolder.files.length > 30 && (
                              <div className='understanding-view__more'>
                                +{subFolder.files.length - 30} more files
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              ))}
          </div>
        )}

        {/* ── Dependencies Tab ─────────────────────────────────────── */}
        {tab === 'deps' && deps && (
          <div className='understanding-view__deps'>
            <div className='understanding-view__struct-summary'>
              {deps.total_modules} Python modules analyzed
            </div>

            {deps.most_imported?.length > 0 && (
              <div className='understanding-view__section'>
                <h3>Most Imported (Core Modules) — click to inspect</h3>
                {deps.most_imported.map(m => (
                  <div
                    key={m.module}
                    className={`understanding-view__dep-row ${
                      selectedModule === m.module
                        ? 'understanding-view__dep-row--selected'
                        : ''
                    }`}
                    onClick={() =>
                      setSelectedModule(
                        selectedModule === m.module ? null : m.module
                      )
                    }
                  >
                    <code>{m.module.replace('app.', '')}</code>
                    <span className='understanding-view__dep-count'>
                      {m.imported_by_count} importers
                    </span>
                  </div>
                ))}
              </div>
            )}

            {selectedModule && deps.modules?.[selectedModule] && (
              <div className='understanding-view__dep-detail'>
                <h3>
                  Module: <code>{selectedModule.replace('app.', '')}</code>
                </h3>
                <div className='understanding-view__dep-lists'>
                  <div>
                    <h4>
                      Imports ({deps.modules[selectedModule].imports.length})
                    </h4>
                    {deps.modules[selectedModule].imports.map(imp => (
                      <code key={imp} className='understanding-view__imp'>
                        {imp.replace('app.', '')}
                      </code>
                    ))}
                    {deps.modules[selectedModule].imports.length === 0 && (
                      <span className='understanding-view__empty-small'>
                        No internal imports
                      </span>
                    )}
                  </div>
                  <div>
                    <h4>
                      Imported by (
                      {deps.modules[selectedModule].imported_by.length})
                    </h4>
                    {deps.modules[selectedModule].imported_by.map(imp => (
                      <code
                        key={imp}
                        className='understanding-view__imp understanding-view__imp--by'
                      >
                        {imp.replace('app.', '')}
                      </code>
                    ))}
                    {deps.modules[selectedModule].imported_by.length === 0 && (
                      <span className='understanding-view__empty-small'>
                        Not imported by others
                      </span>
                    )}
                  </div>
                </div>
                <div className='understanding-view__ext-imports'>
                  <h4>External libraries</h4>
                  <div className='understanding-view__ext-list'>
                    {deps.modules[selectedModule].external_imports.map(ext => (
                      <span key={ext} className='understanding-view__ext-tag'>
                        {ext}
                      </span>
                    ))}
                    {deps.modules[selectedModule].external_imports.length ===
                      0 && (
                      <span className='understanding-view__empty-small'>
                        None
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Search Tab ─────────────────────────────────────────────── */}
        {tab === 'search' && (
          <div className='understanding-view__search'>
            {/* Quick search by type */}
            <div className='understanding-view__quick-search'>
              <div className='understanding-view__quick-type'>
                {['keyword', 'function', 'class'].map(t => (
                  <button
                    key={t}
                    className={`understanding-view__type-btn ${
                      quickType === t
                        ? 'understanding-view__type-btn--active'
                        : ''
                    }`}
                    onClick={() => setQuickType(t)}
                  >
                    {t === 'keyword'
                      ? '🔍 Keyword'
                      : t === 'function'
                      ? '⚡ Function'
                      : '🏛 Class'}
                  </button>
                ))}
              </div>
              <form
                onSubmit={handleQuickSearch}
                className='understanding-view__search-form'
              >
                <input
                  type='text'
                  value={quickQuery}
                  onChange={e => setQuickQuery(e.target.value)}
                  placeholder={
                    quickType === 'function'
                      ? 'Function name, e.g. "chat"'
                      : quickType === 'class'
                      ? 'Class name, e.g. "OllamaService"'
                      : 'Search term, e.g. "ollama_service"'
                  }
                  disabled={searchLoading}
                />
                <button
                  type='submit'
                  disabled={searchLoading || !quickQuery.trim()}
                >
                  {searchLoading ? 'Searching...' : 'Search'}
                </button>
              </form>
            </div>

            {/* Advanced regex search */}
            <details className='understanding-view__advanced'>
              <summary>Advanced (regex)</summary>
              <form
                onSubmit={handleSearch}
                className='understanding-view__search-form'
                style={{ marginTop: '10px' }}
              >
                <input
                  type='text'
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder='Regex pattern, e.g. @router\.(get|post)'
                  disabled={searchLoading}
                />
                <label className='understanding-view__regex-label'>
                  <input
                    type='checkbox'
                    checked={searchRegex}
                    onChange={e => setSearchRegex(e.target.checked)}
                  />
                  Regex
                </label>
                <button
                  type='submit'
                  disabled={searchLoading || !searchQuery.trim()}
                >
                  {searchLoading ? '...' : '🔍'}
                </button>
              </form>
            </details>

            {searchResults && (
              <div className='understanding-view__search-results'>
                <div className='understanding-view__search-meta'>
                  {searchResults.total_matches} matches in{' '}
                  {searchResults.files_searched} files
                </div>
                {searchResults.matches.map((match, i) => (
                  <div key={i} className='understanding-view__match'>
                    <div className='understanding-view__match-header'>
                      <code className='understanding-view__match-file'>
                        {match.relative_path}
                      </code>
                      <span className='understanding-view__match-line'>
                        line {match.line_number}
                      </span>
                    </div>
                    {match.context_before.map((l, j) => (
                      <div
                        key={j}
                        className='understanding-view__match-context'
                      >
                        {l}
                      </div>
                    ))}
                    <div className='understanding-view__match-line-content'>
                      {match.line_content}
                    </div>
                    {match.context_after.map((l, j) => (
                      <div
                        key={j}
                        className='understanding-view__match-context'
                      >
                        {l}
                      </div>
                    ))}
                  </div>
                ))}
                {searchResults.matches.length === 0 && (
                  <div className='understanding-view__no-results'>
                    No matches found for "{searchResults.query}"
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Routes Tab ─────────────────────────────────────────────── */}
        {tab === 'routes' && routes && (
          <div className='understanding-view__routes'>
            <div className='understanding-view__struct-summary'>
              {routes.total_matches} API route definitions found
            </div>
            {routes.matches.map((match, i) => (
              <div key={i} className='understanding-view__route'>
                <div className='understanding-view__route-header'>
                  <code className='understanding-view__route-file'>
                    {match.relative_path.split('/').pop()}
                  </code>
                  <span className='understanding-view__route-line'>
                    line {match.line_number}
                  </span>
                </div>
                <div className='understanding-view__route-content'>
                  {match.line_content.trim()}
                </div>
                {match.context_after[0] && (
                  <div className='understanding-view__route-handler'>
                    {match.context_after[0].trim()}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
