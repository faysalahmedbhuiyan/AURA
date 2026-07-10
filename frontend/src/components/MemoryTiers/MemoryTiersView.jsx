/**
 * AURA Frontend — Memory Tiers View.
 *
 * File: src/components/MemoryTiers/MemoryTiersView.jsx
 * Purpose: Interface for AURA's Advanced Memory System (Phase 13):
 *          Personal Memory, Decision Records, and the Learning Queue.
 *          Queue items only become permanent after explicit confirm.
 */

import { useState, useEffect } from 'react'
import {
  listPersonalMemory,
  deletePersonalMemory,
  createPersonalMemory,
  listDecisionRecords,
  createDecisionRecord,
  listLearningQueue,
  addToLearningQueue,
  confirmQueueItem,
  rejectQueueItem
} from '../../services/api'
import './MemoryTiersView.css'

const TABS = [
  { id: 'personal', label: 'Personal' },
  { id: 'decisions', label: 'Decisions' },
  { id: 'queue', label: 'Learning Queue' }
]

export default function MemoryTiersView () {
  const [tab, setTab] = useState('queue')

  const [personal, setPersonal] = useState([])
  const [pKey, setPKey] = useState('')
  const [pValue, setPValue] = useState('')

  const [decisions, setDecisions] = useState([])
  const [dTitle, setDTitle] = useState('')
  const [dContext, setDContext] = useState('')
  const [dDecision, setDDecision] = useState('')

  const [queue, setQueue] = useState([])
  const [qTarget, setQTarget] = useState('personal')
  const [qTitle, setQTitle] = useState('')
  const [qKey, setQKey] = useState('')
  const [qValue, setQValue] = useState('')
  const [qContext, setQContext] = useState('')
  const [qDecision, setQDecision] = useState('')

  const loadPersonal = async () =>
    setPersonal((await listPersonalMemory()).data)
  const loadDecisions = async () =>
    setDecisions((await listDecisionRecords()).data)
  const loadQueue = async () => setQueue((await listLearningQueue()).data)

  useEffect(() => {
    if (tab === 'personal') loadPersonal()
    if (tab === 'decisions') loadDecisions()
    if (tab === 'queue') loadQueue()
  }, [tab])

  const handleAddPersonal = async e => {
    e.preventDefault()
    if (!pKey.trim() || !pValue.trim()) return
    await createPersonalMemory({ key: pKey.trim(), value: pValue.trim() })
    setPKey('')
    setPValue('')
    loadPersonal()
  }

  const handleDeletePersonal = async id => {
    await deletePersonalMemory(id)
    loadPersonal()
  }

  const handleAddDecision = async e => {
    e.preventDefault()
    if (!dTitle.trim() || !dContext.trim() || !dDecision.trim()) return
    await createDecisionRecord({
      title: dTitle.trim(),
      context: dContext.trim(),
      decision: dDecision.trim()
    })
    setDTitle('')
    setDContext('')
    setDDecision('')
    loadDecisions()
  }

  const handleAddQueueItem = async e => {
    e.preventDefault()
    if (!qTitle.trim()) return

    let payload = {}
    if (qTarget === 'personal') {
      if (!qKey.trim() || !qValue.trim()) return
      payload = { key: qKey.trim(), value: qValue.trim() }
    } else {
      if (!qContext.trim() || !qDecision.trim()) return
      payload = {
        title: qTitle.trim(),
        context: qContext.trim(),
        decision: qDecision.trim()
      }
    }

    await addToLearningQueue({
      target_tier: qTarget,
      title: qTitle.trim(),
      payload,
      source: 'manual'
    })
    setQTitle('')
    setQKey('')
    setQValue('')
    setQContext('')
    setQDecision('')
    loadQueue()
  }

  const handleConfirm = async id => {
    await confirmQueueItem(id)
    loadQueue()
  }

  const handleReject = async id => {
    await rejectQueueItem(id)
    loadQueue()
  }

  return (
    <div className='memory-tiers-view'>
      <div className='memory-tiers-view__tabs'>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`memory-tiers-view__tab ${
              tab === t.id ? 'memory-tiers-view__tab--active' : ''
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'personal' && (
        <div className='memory-tiers-view__panel'>
          <form
            onSubmit={handleAddPersonal}
            className='memory-tiers-view__form'
          >
            <input
              type='text'
              placeholder='Key (e.g. preferred_language)'
              value={pKey}
              onChange={e => setPKey(e.target.value)}
            />
            <input
              type='text'
              placeholder='Value'
              value={pValue}
              onChange={e => setPValue(e.target.value)}
            />
            <button type='submit'>Add</button>
          </form>
          {personal.map(p => (
            <div key={p.id} className='memory-tiers-view__item'>
              <div>
                <strong>{p.key}</strong>: {p.value}
                <span className='memory-tiers-view__category'>
                  {p.category}
                </span>
              </div>
              <button onClick={() => handleDeletePersonal(p.id)}>Delete</button>
            </div>
          ))}
        </div>
      )}

      {tab === 'decisions' && (
        <div className='memory-tiers-view__panel'>
          <form
            onSubmit={handleAddDecision}
            className='memory-tiers-view__form memory-tiers-view__form--column'
          >
            <input
              type='text'
              placeholder='Title'
              value={dTitle}
              onChange={e => setDTitle(e.target.value)}
            />
            <textarea
              rows={2}
              placeholder='Context — why was this decision needed?'
              value={dContext}
              onChange={e => setDContext(e.target.value)}
            />
            <textarea
              rows={2}
              placeholder='Decision — what was decided?'
              value={dDecision}
              onChange={e => setDDecision(e.target.value)}
            />
            <button type='submit'>Record Decision</button>
          </form>
          {decisions.map(d => (
            <div key={d.id} className='memory-tiers-view__decision'>
              <h4>
                {d.title}{' '}
                <span className='memory-tiers-view__status'>{d.status}</span>
              </h4>
              <p>
                <strong>Context:</strong> {d.context}
              </p>
              <p>
                <strong>Decision:</strong> {d.decision}
              </p>
            </div>
          ))}
        </div>
      )}

      {tab === 'queue' && (
        <div className='memory-tiers-view__panel'>
          <div className='memory-tiers-view__notice'>
            Nothing here is permanent until confirmed.
          </div>

          <form
            onSubmit={handleAddQueueItem}
            className='memory-tiers-view__form memory-tiers-view__form--column'
          >
            <select value={qTarget} onChange={e => setQTarget(e.target.value)}>
              <option value='personal'>Personal Memory</option>
              <option value='decision'>Decision Record</option>
            </select>
            <input
              type='text'
              placeholder='Title'
              value={qTitle}
              onChange={e => setQTitle(e.target.value)}
            />
            {qTarget === 'personal' ? (
              <>
                <input
                  type='text'
                  placeholder='Key'
                  value={qKey}
                  onChange={e => setQKey(e.target.value)}
                />
                <input
                  type='text'
                  placeholder='Value'
                  value={qValue}
                  onChange={e => setQValue(e.target.value)}
                />
              </>
            ) : (
              <>
                <textarea
                  rows={2}
                  placeholder='Context'
                  value={qContext}
                  onChange={e => setQContext(e.target.value)}
                />
                <textarea
                  rows={2}
                  placeholder='Decision'
                  value={qDecision}
                  onChange={e => setQDecision(e.target.value)}
                />
              </>
            )}
            <button type='submit'>Add to Queue</button>
          </form>

          {queue.map(item => (
            <div key={item.id} className='memory-tiers-view__queue-item'>
              <div className='memory-tiers-view__queue-header'>
                <strong>{item.title}</strong>
                <span
                  className={`memory-tiers-view__status memory-tiers-view__status--${item.status}`}
                >
                  {item.status}
                </span>
              </div>
              <div className='memory-tiers-view__queue-meta'>
                → {item.target_tier} | source: {item.source}
              </div>
              {item.status === 'pending' && (
                <div className='memory-tiers-view__queue-actions'>
                  <button
                    className='memory-tiers-view__confirm'
                    onClick={() => handleConfirm(item.id)}
                  >
                    Confirm
                  </button>
                  <button
                    className='memory-tiers-view__reject'
                    onClick={() => handleReject(item.id)}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
