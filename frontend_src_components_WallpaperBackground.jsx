name=frontend/src/components/WallpaperBackground.jsx
import React, { useEffect, useState } from 'react'

export default function WallpaperBackground({ clientId }) {
  const [current, setCurrent] = useState(null)
  const [nextImg, setNextImg] = useState(null)
  const [fade, setFade] = useState(false)

  useEffect(() => { loadRandom() }, [])

  async function loadRandom() {
    try {
      const res = await fetch('/api/wallpapers/random')
      if (!res.ok) return
      const data = await res.json()
      if (!data.url) return
      const url = data.url
      setNextImg(url)
      // small delay to allow transition
      setTimeout(() => {
        setCurrent(url)
        setFade(true)
        setTimeout(() => setFade(false), 800)
      }, 50)
    } catch (e) {}
  }

  // Provide a public function that other components might call by window (simple)
  useEffect(() => {
    window.reloadWallpaper = loadRandom
    return () => { window.reloadWallpaper = null }
  }, [])

  return (
    <div className="wallpaper-root" aria-hidden>
      {current && <div className={`wallpaper-img ${fade ? 'fade-in' : ''}`} style={{ backgroundImage: `url(${current})` }} />}
      {!current && <div className="wallpaper-placeholder" />}
      <style>{`
        .wallpaper-root { position: fixed; inset: 0; z-index: -1; overflow: hidden; }
        .wallpaper-img, .wallpaper-placeholder { position: absolute; inset: 0; background-size: cover; background-position: center; transition: opacity 0.8s ease; opacity: 1; }
        .wallpaper-img.fade-in { opacity: 1; }
        .wallpaper-placeholder { background: linear-gradient(180deg, #e9f4f7, #f6eef9); }
      `}</style>
    </div>
  )
}