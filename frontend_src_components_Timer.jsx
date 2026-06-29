name=frontend/src/components/Timer.jsx
import React, { useEffect, useState, useRef } from 'react'
import Airplane from './Airplane'

function formatTime(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0')
  const s = Math.floor(sec % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export default function Timer({ clientId }) {
  const [task, setTask] = useState('')
  const [studyMinutes, setStudyMinutes] = useState(52)
  const [breakMinutes, setBreakMinutes] = useState(17)
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('session_id') || null)
  const [session, setSession] = useState(null)
  const [remaining, setRemaining] = useState(0)
  const [running, setRunning] = useState(false)
  const [showAirplane, setShowAirplane] = useState(false)
  const tickRef = useRef(null)

  useEffect(() => {
    if (sessionId) {
      fetchSession(sessionId)
    }
    // keyboard space handling
    const onKey = (e) => {
      if (e.code === 'Space') {
        e.preventDefault()
        toggleStartPause()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  useEffect(() => {
    // update remaining every second on client when running
    if (session && !session.paused && session.end_time) {
      if (tickRef.current) clearInterval(tickRef.current)
      tickRef.current = setInterval(() => {
        const end = new Date(session.end_time).getTime()
        const now = Date.now()
        let r = Math.max(0, Math.round((end - now) / 1000))
        setRemaining(r)
        checkAirplane(session, r)
        if (r <= 0) {
          clearInterval(tickRef.current)
          onSessionComplete()
        }
      }, 1000)
      setRunning(true)
      return () => clearInterval(tickRef.current)
    } else {
      setRunning(false)
      if (tickRef.current) clearInterval(tickRef.current)
    }
  }, [session])

  function checkAirplane(sessionObj, rem) {
    if (!sessionObj) return
    if (!sessionObj.airplane_checked_times) sessionObj.airplane_checked_times = {}
    const totalStudy = sessionObj.study_minutes * 60
    // show every 15 minutes (900s) for long sessions
    if (sessionObj.phase === 'study') {
      const thresholds = []
      for (let t = totalStudy - 900; t > 0; t -= 900) thresholds.push(t)
      thresholds.push(300) // 5 minutes before end
      for (const th of thresholds) {
        const key = `th_${th}`
        if (rem <= th && !sessionObj.airplane_checked_times[key]) {
          sessionObj.airplane_checked_times[key] = true
          triggerAirplane()
        }
      }
    }
  }

  function triggerAirplane() {
    setShowAirplane(true)
    setTimeout(() => setShowAirplane(false), 7000)
  }

  async function fetchSession(id) {
    try {
      const res = await fetch(`/api/sessions/${id}`)
      if (!res.ok) throw new Error('no session')
      const data = await res.json()
      setSession(data)
    } catch (e) {
      localStorage.removeItem('session_id')
      setSessionId(null)
      setSession(null)
    }
  }

  async function startSession() {
    const payload = { client_id: clientId, task_text: task, study_minutes: studyMinutes, break_minutes: breakMinutes }
    const res = await fetch('/api/sessions/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    const data = await res.json()
    localStorage.setItem('session_id', data.session_id)
    setSessionId(data.session_id)
    fetchSession(data.session_id)
  }

  async function pause() {
    if (!sessionId) return
    await fetch('/api/sessions/pause', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) })
    fetchSession(sessionId)
  }

  async function resume() {
    if (!sessionId) return
    await fetch('/api/sessions/resume', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) })
    fetchSession(sessionId)
  }

  async function reset() {
    if (!sessionId) return
    await fetch('/api/sessions/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) })
    localStorage.removeItem('session_id')
    setSessionId(null)
    setSession(null)
    setRemaining(0)
  }

  async function skip() {
    if (!sessionId) return
    await fetch('/api/sessions/skip', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId }) })
    fetchSession(sessionId)
  }

  async function onSessionComplete() {
    if (!session) return
    // Mark completed (simple)
    await fetch('/api/history/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        task_text: session.task_text || '',
        study_duration_seconds: session.study_minutes * 60,
        break_duration_seconds: session.break_minutes * 60
      })
    })
    // fetch new wallpaper
    try { await fetch('/api/wallpapers/random') } catch (e) {}
    // reset local
    localStorage.removeItem('session_id')
    setSession(null)
    setSessionId(null)
    setRemaining(0)
  }

  function toggleStartPause() {
    if (!session) {
      startSession()
    } else if (session.paused) {
      resume()
    } else {
      pause()
    }
  }

  const pct = session && session.phase && session.start_time && session.end_time
    ? Math.max(0, Math.min(1, ( (new Date(session.end_time).getTime() - Date.now()) / ((new Date(session.end_time).getTime() - new Date(session.start_time).getTime())) )))
    : 0

  return (
    <div className="timer-card">
      <div className="task-entry">
        <input className="task-input" placeholder="Enter task (e.g., Study Chapter 3)" value={task} onChange={(e) => setTask(e.target.value)} />
      </div>

      <div className="controls-row">
        <label>Study
          <input type="number" min="1" value={studyMinutes} onChange={(e) => setStudyMinutes(Number(e.target.value))} />
        </label>
        <label>Break
          <input type="number" min="1" value={breakMinutes} onChange={(e) => setBreakMinutes(Number(e.target.value))} />
        </label>
      </div>

      <div className="timer-display">
        <svg className="progress-ring" viewBox="0 0 120 120">
          <circle className="ring-bg" cx="60" cy="60" r="54" strokeWidth="12" />
          <circle className="ring-fg" cx="60" cy="60" r="54" strokeWidth="12" style={{ strokeDasharray: `${Math.PI*2*54}`, strokeDashoffset: `${(1 - pct) * Math.PI * 2 * 54}` }} />
          <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" className="time-text">{formatTime(remaining)}</text>
        </svg>
        <div className="session-info">
          <div className="phase">{session ? (session.phase === 'study' ? 'Study' : session.phase === 'break' ? 'Break' : 'Idle') : 'Idle'}</div>
          <div className="current-task">{session ? session.task_text : 'No task'}</div>
        </div>
      </div>

      <div className="button-row">
        <button onClick={toggleStartPause}>{!session ? 'Start' : session.paused ? 'Resume' : 'Pause'}</button>
        <button onClick={reset}>Reset</button>
        <button onClick={skip}>Skip</button>
      </div>

      {showAirplane && <Airplane text={session?.task_text || task || 'Study'} />}

    </div>
  )
}