# Pomodoro Study App

A calm, beautiful Pomodoro study application optimized for Render's Free Web Service (512 MB RAM).

This repository contains a minimal full-stack scaffold (FastAPI backend + Vite React frontend) with:

- Server-backed Pomodoro sessions (start/pause/resume/reset)
- Task entry and history
- Wallpaper downloader that caches horizontal landscape images
- A hand-drawn pink airplane reminder animation on the frontend
- Render manifest (render.yaml) and deployment instructions

Quick start (local):

1. Backend: 
   - Create a virtualenv: `python -m venv .venv && source .venv/bin/activate`
   - Install: `pip install -r backend/requirements.txt`
   - Run: `uvicorn backend.main:app --reload`

2. Frontend (dev):
   - `cd frontend && npm install && npm run dev`

Build for production (single service):

- The Render manifest builds the frontend, installs Python deps, then serves with Uvicorn. See `render.yaml`.

Notes:
- This scaffold is single-user by default (client_id stored in localStorage). For multi-user deployments add authentication.
- The wallpaper downloader SOURCES list must be filled with direct image URLs from the allowed site. The downloader runs once at startup and caches images to `/wallpapers`.

License: MIT
