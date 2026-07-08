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

export default api
