name=frontend/src/App.jsx
import React, { useEffect, useState } from 'react'
import Timer from './components/Timer'
import WallpaperBackground from './components/WallpaperBackground'

export default function App() {
  const [clientId] = useState(() => {
    let id = localStorage.getItem('client_id')
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem('client_id', id)
    }
    return id
  })

  return (
    <div className="app-root">
      <WallpaperBackground clientId={clientId} />
      <main className="container">
        <h1 className="title">Calm Pomodoro</h1>
        <Timer clientId={clientId} />
      </main>
    </div>
  )
}