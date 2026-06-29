name=frontend/src/components/Airplane.jsx
import React from 'react'
import './airplane.css'

export default function Airplane({ text = '' }) {
  return (
    <div className="airplane-wrapper">
      <svg className="airplane" width="220" height="80" viewBox="0 0 220 80" xmlns="http://www.w3.org/2000/svg" aria-hidden>
        <defs>
          <style>{`.banner { fill: #ffc0db; } .plane { fill:#ff66b2; } .banner-text { font-size:12px; fill:#4b004b; font-family: sans-serif; }`}</style>
        </defs>
        <g transform="translate(0,0)">
          <rect x="60" y="20" rx="6" ry="6" width="140" height="28" className="banner" />
          <text x="130" y="38" textAnchor="middle" className="banner-text">{text}</text>
          <g transform="translate(20,34) scale(0.9)">
            <path className="plane" d="M0 0 L20 -8 L32 -4 L46 -14 L52 -10 L44 -2 L60 2 L52 8 L46 4 L32 14 L20 10 Z" />
          </g>
        </g>
      </svg>
      <style>{`
        .airplane-wrapper {
          position: fixed;
          top: 12%;
          left: -30%;
          z-index: 9999;
          pointer-events: none;
          animation: fly-across 6s cubic-bezier(.2,.8,.2,1) forwards;
        }
        @keyframes fly-across {
          0% { transform: translateX(0) translateY(0) rotate(-6deg); opacity: 0 }
          10% { opacity: 1 }
          100% { transform: translateX(140vw) translateY(-10vh) rotate(4deg); opacity: 0.95 }
        }
      `}</style>
    </div>
  )
}