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
  timeout: 120000, // 2 min — LLM responses can be slow
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

export default api
