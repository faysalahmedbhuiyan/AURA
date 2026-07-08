/**
 * AURA Frontend — Agent View.
 *
 * File: src/components/Agents/AgentView.jsx
 * Purpose: Interface for interacting with AURA's agents.
 *          File operations, system monitoring.
 */

import { useState, useEffect } from 'react'
import { executeAgent, getAgentHealth } from '../../services/api'
import './AgentView.css'

export default function AgentView () {
  const [health, setHealth] = useState(null)
  const [activeAgent, setActiveAgent] = useState('system')
  const [action, setAction] = useState('health')
  const [params, setParams] = useState('{}')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadHealth()
  }, [])

  const loadHealth = async () => {
    try {
      const res = await getAgentHealth()
      setHealth(res.data)
    } catch (err) {
      console.error('Health check failed:', err)
    }
  }

  const handleExecute = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    let parsedParams = {}
    try {
      parsedParams = JSON.parse(params)
    } catch {
      setError('Invalid JSON in params field')
      setLoading(false)
      return
    }

    try {
      const res = await executeAgent(activeAgent, action, parsedParams)
      setResult(res.data)
      if (action === 'health') loadHealth()
    } catch (err) {
      setError(err.message || 'Agent execution failed')
    } finally {
      setLoading(false)
    }
  }

  const AGENTS = {
    system: {
      label: '🖥️ System',
      actions: ['health', 'ram', 'cpu', 'disk', 'info', 'processes']
    },
    file: {
      label: '📁 File',
      actions: ['list', 'read', 'write', 'search', 'info', 'exists']
    }
  }

  const QUICK_ACTIONS = [
    { label: '💾 RAM Status', agent: 'system', action: 'ram', params: '{}' },
    { label: '⚡ CPU Status', agent: 'system', action: 'cpu', params: '{}' },
    { label: '💿 Disk Status', agent: 'system', action: 'disk', params: '{}' },
    {
      label: '📋 Processes',
      agent: 'system',
      action: 'processes',
      params: '{"top_n": 5}'
    },
    {
      label: '📂 List AURA',
      agent: 'file',
      action: 'list',
      params: '{"path": "D:/AURA"}'
    }
  ]

  const statusColor = status =>
    ({
      ok: '#4caf7d',
      warning: '#f5a623',
      critical: '#e74c3c'
    }[status] || '#666')

  return (
    <div className='agent-view'>
      {/* Health Summary */}
      {health?.data && (
        <div className='agent-view__health'>
          <div
            className='agent-view__health-dot'
            style={{ background: statusColor(health.data.overall) }}
          />
          <span className='agent-view__health-label'>
            System: {health.data.overall?.toUpperCase()}
          </span>
          <span className='agent-view__health-meta'>
            RAM {health.data.ram?.used_percent}% • CPU{' '}
            {health.data.cpu?.used_percent}%
          </span>
          <button className='agent-view__refresh' onClick={loadHealth}>
            ↻
          </button>
        </div>
      )}

      {/* Quick Actions */}
      <div className='agent-view__quick'>
        <h3>Quick Actions</h3>
        <div className='agent-view__quick-grid'>
          {QUICK_ACTIONS.map(qa => (
            <button
              key={qa.label}
              className='agent-view__quick-btn'
              onClick={() => {
                setActiveAgent(qa.agent)
                setAction(qa.action)
                setParams(qa.params)
              }}
            >
              {qa.label}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Executor */}
      <div className='agent-view__executor'>
        <h3>Agent Executor</h3>

        <div className='agent-view__controls'>
          <div className='agent-view__field'>
            <label>Agent</label>
            <div className='agent-view__agent-tabs'>
              {Object.entries(AGENTS).map(([id, info]) => (
                <button
                  key={id}
                  className={`agent-view__agent-tab ${
                    activeAgent === id ? 'agent-view__agent-tab--active' : ''
                  }`}
                  onClick={() => {
                    setActiveAgent(id)
                    setAction(info.actions[0])
                  }}
                >
                  {info.label}
                </button>
              ))}
            </div>
          </div>

          <div className='agent-view__field'>
            <label>Action</label>
            <div className='agent-view__action-tabs'>
              {AGENTS[activeAgent].actions.map(a => (
                <button
                  key={a}
                  className={`agent-view__action-tab ${
                    action === a ? 'agent-view__action-tab--active' : ''
                  }`}
                  onClick={() => setAction(a)}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          <div className='agent-view__field'>
            <label>Params (JSON)</label>
            <textarea
              value={params}
              onChange={e => setParams(e.target.value)}
              rows={3}
              className='agent-view__params'
              placeholder='{"path": "D:/AURA"}'
            />
          </div>

          <button
            className='agent-view__execute'
            onClick={handleExecute}
            disabled={loading}
          >
            {loading ? '⏳ Running...' : '▶ Execute'}
          </button>
        </div>

        {error && <div className='agent-view__error'>⚠️ {error}</div>}

        {result && (
          <div className='agent-view__result'>
            <div className='agent-view__result-header'>
              <span
                className={
                  result.success ? 'agent-view__success' : 'agent-view__failure'
                }
              >
                {result.success ? '✅ Success' : '❌ Failed'}
              </span>
              <span className='agent-view__result-action'>
                {result.agent} → {result.action}
              </span>
            </div>
            <pre className='agent-view__result-data'>
              {JSON.stringify(result.data || result.error, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
