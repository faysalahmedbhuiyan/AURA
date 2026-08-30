/**
 * AURA Frontend — Goals View.
 *
 * File: src/components/Goals/GoalsView.jsx
 * Purpose: Interface for the Goal Manager (Phase 16). Create a goal,
 *          AURA breaks it into milestones/tasks, track progress and
 *          blockers, and update task status.
 */

import { useState, useEffect } from 'react'
import {
  createGoal,
  listGoals,
  getGoalProgress,
  updateTaskStatus
} from '../../services/api'
import './GoalsView.css'

const STATUS_OPTIONS = ['not_started', 'in_progress', 'blocked', 'completed']
const STATUS_COLOR = {
  not_started: '#888',
  in_progress: '#6ab7ff',
  blocked: '#e74c3c',
  completed: '#4caf7d'
}

export default function GoalsView () {
  const [goals, setGoals] = useState([])
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [creating, setCreating] = useState(false)
  const [progressMap, setProgressMap] = useState({})

  const loadGoals = async () => {
    const res = await listGoals()
    setGoals(res.data)
    for (const g of res.data) {
      const p = await getGoalProgress(g.id)
      setProgressMap(prev => ({ ...prev, [g.id]: p.data }))
    }
  }

  useEffect(() => {
    loadGoals()
  }, [])

  const handleCreate = async e => {
    e.preventDefault()
    if (!title.trim()) return
    setCreating(true)
    try {
      await createGoal(title.trim(), description.trim() || null)
      setTitle('')
      setDescription('')
      loadGoals()
    } finally {
      setCreating(false)
    }
  }

  const handleStatusChange = async (taskId, newStatus, goalId) => {
    await updateTaskStatus(taskId, newStatus)
    loadGoals()
  }

  return (
    <div className='goals-view'>
      <form onSubmit={handleCreate} className='goals-view__form'>
        <input
          type='text'
          placeholder='Goal title, e.g. "Launch v1.0 of my app"'
          value={title}
          onChange={e => setTitle(e.target.value)}
        />
        <textarea
          rows={2}
          placeholder='Optional context for AURA to plan around...'
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        <button type='submit' disabled={creating || !title.trim()}>
          {creating ? 'Planning...' : 'Create Goal (AURA plans it)'}
        </button>
      </form>

      {goals.map(goal => {
        const progress = progressMap[goal.id]
        return (
          <div key={goal.id} className='goals-view__goal'>
            <div className='goals-view__goal-header'>
              <h3>{goal.title}</h3>
              {progress && (
                <span className='goals-view__progress'>
                  {progress.completed_tasks}/{progress.total_tasks} (
                  {progress.percent}%)
                </span>
              )}
            </div>
            {progress?.blockers?.length > 0 && (
              <div className='goals-view__blockers'>
                {progress.blockers.map((b, i) => (
                  <div key={i} className='goals-view__blocker'>
                    ⚠ {b.title}: {b.reason}
                  </div>
                ))}
              </div>
            )}
            {goal.milestones.map(m => (
              <div key={m.id} className='goals-view__milestone'>
                <h4>{m.title}</h4>
                {m.tasks.map(t => (
                  <div key={t.id} className='goals-view__task'>
                    <span>{t.title}</span>
                    <select
                      value={t.status}
                      style={{ color: STATUS_COLOR[t.status] }}
                      onChange={e =>
                        handleStatusChange(t.id, e.target.value, goal.id)
                      }
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s} value={s}>
                          {s.replace('_', ' ')}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
