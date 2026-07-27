/**
 * AURA Frontend — API Service.
 *
 * File: src/services/api.js
 * Purpose: Centralized HTTP client for all AURA backend API calls.
 *          All components use this service — never call axios directly.
 *          Base URL configured for local FastAPI backend.
 */

import axios from 'axios'

// ── Axios Instance ────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 320000, // 2 min — LLM responses can be slow
  headers: {
    'Content-Type': 'application/json'
  }
})

// ── Request Interceptor ───────────────────────────────────────────────────────
api.interceptors.request.use(
  config => {
    // Log requests in development
    if (import.meta.env.DEV) {
      console.log(`[AURA API] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  error => Promise.reject(error)
)

// ── Response Interceptor ──────────────────────────────────────────────────────
api.interceptors.response.use(
  response => response,
  error => {
    const message = error.response?.data?.detail || error.message
    console.error(`[AURA API Error] ${message}`)
    return Promise.reject(new Error(message))
  }
)

// ── API Methods ───────────────────────────────────────────────────────────────

/**
 * Check backend health status.
 * @returns {Promise<Object>} Health response
 */
export const checkHealth = () => api.get('/health')

/**
 * Check database health status.
 * @returns {Promise<Object>} DB health response
 */
export const checkDBHealth = () => api.get('/db-health')

/**
 * Send a chat message to AURA.
 * @param {string} message - User message text
 * @param {string|null} conversationId - Existing conversation UUID
 * @param {string} language - Language code (bn, en, hi, ko)
 * @returns {Promise<Object>} Chat response with conversation_id
 */
export const sendMessage = (message, conversationId = null, language = 'en') =>
  api.post('/chat', {
    message,
    conversation_id: conversationId,
    language
  })

/**
 * Get conversation history by ID.
 * @param {string} conversationId - Conversation UUID
 * @returns {Promise<Object>} Conversation with messages
 */
export const getConversation = conversationId =>
  api.get(`/chat/${conversationId}`)

/**
 * Convert text to speech audio.
 * @param {string} text - Text to speak
 * @param {string} language - Language code
 * @returns {Promise<Blob>} WAV audio blob
 */
export const textToSpeech = async (text, language = 'en') => {
  const response = await api.post(
    '/voice/speak',
    { text, language },
    { responseType: 'blob' }
  )
  return response.data
}

/**
 * Transcribe audio file to text.
 * @param {File} audioFile - Audio file object
 * @param {string} language - Language code
 * @returns {Promise<Object>} Transcription result
 */
export const transcribeAudio = async (audioFile, language = 'en') => {
  const formData = new FormData()
  formData.append('file', audioFile)
  formData.append('language', language)
  const response = await api.post('/voice/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

/**
 * Search AURA's semantic memory.
 * @param {string} query - Search query
 * @param {number} nResults - Max results
 * @returns {Promise<Object>} Search results
 */
export const searchMemory = (query, nResults = 5) =>
  api.post('/memory/search', { query, n_results: nResults })

/**
 * Add a knowledge entry (pending confirmation).
 * @param {Object} entry - Knowledge entry data
 * @returns {Promise<Object>} Created entry
 */
export const addKnowledge = entry => api.post('/memory/knowledge', entry)

/**
 * Confirm a knowledge entry for permanent storage.
 * @param {string} entryId - Knowledge entry UUID
 * @returns {Promise<Object>} Confirmed entry
 */
export const confirmKnowledge = entryId =>
  api.post(`/memory/knowledge/${entryId}/confirm`)

/**
 * Get all pending knowledge entries.
 * @returns {Promise<Array>} Pending entries
 */
export const getPendingKnowledge = () => api.get('/memory/knowledge')

/**
 * Get all confirmed knowledge entries.
 * @returns {Promise<Array>} Confirmed entries
 */
export const getConfirmedKnowledge = () =>
  api.get('/memory/knowledge/confirmed')
/**
 * Research a topic from the web (Search → Collect → Verify → Summarize).
 * Does NOT save anything — returns a candidate for review.
 * @param {string} query - Topic to research
 * @param {string} language - Language code
 * @param {number} maxSources - Max sources to search
 * @returns {Promise<Object>} Research candidate {title, summary, sources, suggested_confidence, language}
 */
export const researchTopic = (query, language = 'en', maxSources = 4) =>
  api.post('/knowledge/research', {
    query,
    language,
    max_sources: maxSources
  })
/**
 * Execute an agent action.
 * @param {string} agent - Agent name (file, system)
 * @param {string} action - Action to perform
 * @param {Object} params - Action parameters
 * @returns {Promise<Object>} Agent result
 */
export const executeAgent = (agent, action, params = {}) =>
  api.post('/agents/execute', { agent, action, params })

/**
 * Get system health via System Agent.
 * @returns {Promise<Object>} System health data
 */
export const getAgentHealth = () => api.get('/agents/health')

/**
 * List available agents.
 * @returns {Promise<Array>} Agent list
 */
export const listAgents = () => api.get('/agents/list')
/**
 * Run AURA's Self Review Engine on a file or directory.
 * READ-ONLY — never modifies any file.
 * @param {string} path - Absolute path to analyze
 * @param {number} maxFiles - Max files to scan
 * @returns {Promise<Object>} Review report {debt_summary, suggestions, issues}
 */
export const analyzeCode = (path, maxFiles = 200) =>
  api.post('/review/analyze', { path, max_files: maxFiles })
/**
 * Create an improvement plan from a free-text request.
 * NEVER modifies any file — planning only.
 * @param {string} description - What to improve/change
 * @param {string} projectRoot - Root path to search for affected files
 * @returns {Promise<Object>} Plan {analysis, affected_files, risk, status}
 */
export const createPlan = (description, projectRoot = 'D:/AURA') =>
  api.post('/planning/create', { description, project_root: projectRoot })
/**
 * Apply a confirmed change to a file. REQUIRES confirmed=true.
 * A backup is created automatically before the write.
 * @param {string} path - Absolute file path
 * @param {string} newContent - Full new content for the file
 * @param {boolean} confirmed - Must be true to actually apply
 * @param {string} reason - Short reason for the change
 * @returns {Promise<Object>} Report {success, backup, applied, rollback_instructions}
 */
export const applyChange = (path, newContent, confirmed, reason = '') =>
  api.post('/modification/apply', {
    path,
    new_content: newContent,
    confirmed,
    reason
  })

/**
 * Restore a file from a backup.
 * @param {string} backupPath - Path to the .bak file
 * @returns {Promise<Object>} Report {success, result, error}
 */
export const rollbackChange = backupPath =>
  api.post('/modification/rollback', { backup_path: backupPath })
// ── Rollback API (Phase 11) ───────────────────────────────────────────────────

/**
 * Get current git status.
 * @returns {Promise<Object>} Git status
 */
export const getRollbackStatus = () => api.get('/rollback/status')

/**
 * Get commit history.
 * @param {number} limit - Max commits to return
 * @returns {Promise<Object>} {total, commits}
 */
export const getRollbackLog = (limit = 20) =>
  api.get(`/rollback/log?limit=${limit}`)

/**
 * Preview a rollback without applying it.
 * @param {string} targetRef - Git ref to preview
 * @returns {Promise<Object>} Preview with files that would change
 */
export const previewRollback = targetRef =>
  api.get(`/rollback/preview/${encodeURIComponent(targetRef)}`)

/**
 * Roll back ALL files to a specific commit.
 * @param {string} targetRef - Git commit/branch/tag
 * @param {string} description - Reason for rollback
 * @param {boolean} confirmed - MUST be true
 * @returns {Promise<Object>} Rollback result
 */
export const rollbackToCommit = (targetRef, description, confirmed) =>
  api.post('/rollback/commit', {
    target_ref: targetRef,
    description,
    confirmed
  })

/**
 * Roll back specific files to a commit.
 * @param {string} targetRef - Git ref
 * @param {string[]} filePaths - Files to restore
 * @param {string} description - Reason
 * @param {boolean} confirmed - MUST be true
 * @returns {Promise<Object>} Result
 */
export const rollbackFiles = (targetRef, filePaths, description, confirmed) =>
  api.post('/rollback/files', {
    target_ref: targetRef,
    file_paths: filePaths,
    description,
    confirmed
  })

/**
 * List all named snapshots.
 * @returns {Promise<Object>} {total, snapshots}
 */
export const listSnapshots = () => api.get('/rollback/snapshots')

/**
 * Create a named snapshot.
 * @param {string} name - Snapshot name
 * @param {string} description - Description
 * @param {string} gitRef - Git ref to point to
 * @param {string} phase - Optional phase label
 * @returns {Promise<Object>} Created snapshot
 */
export const createSnapshot = (name, description, gitRef, phase = '') =>
  api.post('/rollback/snapshots', {
    name,
    description,
    git_ref: gitRef,
    phase
  })

/**
 * Restore from a named snapshot.
 * @param {string} snapshotId - Snapshot ID
 * @param {boolean} confirmed - MUST be true
 * @returns {Promise<Object>} Restore result
 */
export const restoreSnapshot = (snapshotId, confirmed) =>
  api.post('/rollback/restore-snapshot', {
    snapshot_id: snapshotId,
    confirmed
  })

/**
 * Delete a snapshot record.
 * @param {string} snapshotId - Snapshot to delete
 * @returns {Promise<Object>} Delete result
 */
export const deleteSnapshot = snapshotId =>
  api.delete(`/rollback/snapshots/${snapshotId}`)

/**
 * Create a journal entry (session log, decision record, or change).
 * @param {Object} entry - {category, title, content, tags, files_created, files_modified, files_deleted, related_phase}
 * @returns {Promise<Object>} Created entry
 */
export const createJournalEntry = entry => api.post('/journal/entries', entry)

/**
 * List journal entries with optional filters.
 * @param {Object} filters - {category, search, limit, offset}
 * @returns {Promise<Array>} Journal entries
 */
export const listJournalEntries = (filters = {}) =>
  api.get('/journal/entries', { params: filters })

/**
 * Generate a journal summary for the last N days.
 * @param {number} days - Lookback window
 * @returns {Promise<Object>} Summary grouped by category
 */
export const getJournalSummary = (days = 7) =>
  api.get('/journal/summary', { params: { days } })
// ── Memory Tiers (Phase 13) ─────────────────────────────────────────────────
export const createPersonalMemory = data =>
  api.post('/memory-tiers/personal', data)
export const listPersonalMemory = () => api.get('/memory-tiers/personal')
export const deletePersonalMemory = id =>
  api.delete(`/memory-tiers/personal/${id}`)

export const createDecisionRecord = data =>
  api.post('/memory-tiers/decisions', data)
export const listDecisionRecords = () => api.get('/memory-tiers/decisions')

export const addToLearningQueue = data => api.post('/memory-tiers/queue', data)
export const listLearningQueue = (statusFilter = null) =>
  api.get('/memory-tiers/queue', {
    params: statusFilter ? { status: statusFilter } : {}
  })
export const confirmQueueItem = id =>
  api.post(`/memory-tiers/queue/${id}/confirm`)
export const rejectQueueItem = id =>
  api.post(`/memory-tiers/queue/${id}/reject`)
// ── Understanding API (Phase 14) ──────────────────────────────────────────────

/**
 * Get high-level project summary.
 * @returns {Promise<Object>} Summary with files, routes, deps
 */
export const getProjectSummary = () => api.get('/understanding/summary')

/**
 * Get complete project structure.
 * @param {number} maxDepth - Max folder depth
 * @returns {Promise<Object>} Full file/folder tree
 */
export const getProjectStructure = (maxDepth = 5) =>
  api.get(`/understanding/structure?max_depth=${maxDepth}`)

/**
 * Get Python dependency graph.
 * @returns {Promise<Object>} Import graph
 */
export const getDependencies = () => api.get('/understanding/dependencies')

/**
 * Search codebase.
 * @param {string} query - Search term
 * @param {boolean} isRegex - Treat as regex
 * @param {string[]} fileTypes - Filter by type
 * @param {number} maxResults - Max results
 * @returns {Promise<Object>} Search results
 */
export const searchCode = (
  query,
  isRegex = false,
  fileTypes = null,
  maxResults = 30
) =>
  api.post('/understanding/search', {
    query,
    is_regex: isRegex,
    file_types: fileTypes,
    max_results: maxResults
  })

/**
 * Get all FastAPI route definitions.
 * @returns {Promise<Object>} Route list
 */
export const getApiRoutes = () => api.get('/understanding/routes')

/**
 * Find a function definition by name.
 * @param {string} name - Function name
 * @returns {Promise<Object>} Matching definitions
 */
export const findFunctionDef = name =>
  api.get(`/understanding/function/${encodeURIComponent(name)}`)

/**
 * Find a class definition by name.
 * @param {string} name - Class name
 * @returns {Promise<Object>} Matching definitions
 */
export const findClassDef = name =>
  api.get(`/understanding/class/${encodeURIComponent(name)}`)
// ── Coding Mentor (Phase 15) ────────────────────────────────────────────────
export const explainFile = (path, language = 'en') =>
  api.post('/mentor/explain', { path, language })

export const teachConcept = (concept, language = 'en') =>
  api.post('/mentor/concept', { concept, language })

export const suggestPractices = path => api.post('/mentor/practices', { path })

export const askMentor = (question, filePath = null, language = 'en') =>
  api.post('/mentor/ask', { question, file_path: filePath, language })
// ── Goal Manager (Phase 16) ─────────────────────────────────────────────────
export const createGoal = (title, description = null, language = 'en') =>
  api.post('/goals', { title, description, language })
export const listGoals = () => api.get('/goals')
export const getGoalProgress = goalId => api.get(`/goals/${goalId}/progress`)
export const updateTaskStatus = (taskId, taskStatus, blockedReason = null) =>
  api.post(`/goals/tasks/${taskId}/status`, {
    status: taskStatus,
    blocked_reason: blockedReason
  })
/**
 * Get conversation list for sidebar history.
 * @param {number} limit - Max conversations
 * @returns {Promise<Array>} Conversation list
 */
export const getConversationList = (limit = 50) =>
  api.get(`/chat?limit=${limit}`)
// ── Voice Session (Phase 21) ────────────────────────────────────────────────
export const getVoiceState = () => api.get('/voice-session/state')
export const setVoiceMode = mode => api.post('/voice-session/mode', { mode })

export const deleteConversation = conversationId =>
  api.delete(`/chat/${conversationId}`)

export const checkWakeWord = async (audioBlob, language = 'en') => {
  const formData = new FormData()
  formData.append('audio', audioBlob)
  formData.append('language', language)
  const res = await api.post('/voice-session/check-wake-word', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}
// ── Research Engine API (Phase 24) ────────────────────────────────────────────

/**
 * Run full autonomous research pipeline.
 */
export const runResearch = (
  query,
  language = 'en',
  maxSources = 6,
  deep = true
) =>
  api.post('/research/run', {
    query,
    language,
    max_sources: maxSources,
    deep
  })

/**
 * Quick search — URLs and snippets only.
 */
export const quickSearch = (query, language = 'en', maxResults = 5) =>
  api.post('/research/quick', { query, language, max_results: maxResults })

/**
 * Save confirmed research to Advanced Memory.
 */
export const saveResearch = (
  title,
  summary,
  query,
  confidence,
  sources,
  language
) =>
  api.post('/research/save', {
    title,
    summary,
    query,
    confidence,
    sources,
    language
  })

/**
 * Add research to learning queue.
 */
export const queueResearch = (title, summary, query, language) =>
  api.post('/research/queue', { title, summary, query, language })

/**
 * Upload a PDF/DOCX for AURA to learn from (Tier 3).
 * Chunks go to the pending queue by default — confirm via
 * confirmSource() or the Intelligence pending list.
 */
export const uploadDocument = async (
  file,
  language = 'en',
  autoConfirm = false
) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('language', language)
  formData.append('auto_confirm', autoConfirm)
  const res = await api.post('/ingestion/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

/**
 * Bulk-confirm every pending item that came from one uploaded file.
 */
export const confirmSource = source =>
  api.post('/ingestion/confirm-source', null, { params: { source } })
/**
 * Create an empty conversation (used before the first message,
 * when attaching a file needs a conversation_id to exist first).
 */
export const createConversation = (language = 'en') =>
  api.post('/chat/new', null, { params: { language } })

/**
 * Attach a PDF/DOCX/image to a conversation. Extracts text but saves
 * NOTHING permanently — the next chat message is an instruction about it.
 */
export const stageFile = async (file, conversationId, language = 'en') => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('conversation_id', conversationId)
  formData.append('language', language)
  const res = await api.post('/ingestion/stage', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

/**
 * Detach the currently staged file without saving it.
 */
export const clearStagedFile = conversationId =>
  api.delete(`/ingestion/stage/${conversationId}`)

export default api
