import os
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, create_engine, Session, select
from models import Setting, Session as PomSession, CompletedTask, Wallpaper
from wallpaper_downloader import run_fetch
import csv
import io

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./db.sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

app = FastAPI(title="Pomodoro Study App")

# CORS (frontend served from same service in prod; allow all for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend build (if present) and wallpapers
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
frontend_dist = os.path.normpath(frontend_dist)
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

wall_dir = os.path.join(os.path.dirname(__file__), "..", "wallpapers")
wall_dir = os.path.normpath(wall_dir)
os.makedirs(wall_dir, exist_ok=True)
app.mount("/wallpapers", StaticFiles(directory=wall_dir), name="wallpapers")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    skip = os.environ.get("RENDER_SKIP_WALLPAPER_DOWNLOAD", "true").lower() in ("1", "true", "yes")
    enable = os.environ.get("RENDER_ENABLE_WALLPAPER_DOWNLOAD", "false").lower() in ("1", "true", "yes")
    if enable and not skip:
        # Run a conservative fetch in background
        from fastapi import BackgroundTasks
        # Use a background task to avoid blocking startup
        BackgroundTasks().add_task(run_fetch, engine, limit=int(os.environ.get("RENDER_WALLPAPER_LIMIT", "20")))

@app.get("/api/healthz")
def healthz():
    return {"status": "ok"}

def get_or_create_setting(client_id: str):
    with Session(engine) as db:
        s = db.exec(select(Setting).where(Setting.client_id == client_id)).first()
        if not s:
            s = Setting(client_id=client_id)
            db.add(s); db.commit(); db.refresh(s)
        return s

@app.post("/api/settings")
def update_settings(payload: dict):
    client_id = payload.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    with Session(engine) as db:
        s = db.exec(select(Setting).where(Setting.client_id == client_id)).first()
        if not s:
            s = Setting(client_id=client_id)
        s.default_study_minutes = int(payload.get("default_study_minutes", s.default_study_minutes))
        s.default_break_minutes = int(payload.get("default_break_minutes", s.default_break_minutes))
        s.wallpaper_rotation = bool(payload.get("wallpaper_rotation", s.wallpaper_rotation))
        s.airplane_reminders_on = bool(payload.get("airplane_reminders_on", s.airplane_reminders_on))
        db.add(s); db.commit(); db.refresh(s)
        return s

@app.get("/api/settings/{client_id}")
def get_settings(client_id: str):
    return get_or_create_setting(client_id)

@app.post("/api/sessions/start")
def start_session(payload: dict):
    client_id = payload.get("client_id") or str(uuid.uuid4())
    task = payload.get("task_text", "")
    study = int(payload.get("study_minutes", 52))
    brk = int(payload.get("break_minutes", 17))
    session_id = str(uuid.uuid4())
    start = datetime.utcnow()
    end = start + timedelta(minutes=study)
    p = PomSession(id=session_id, client_id=client_id, task_text=task, study_minutes=study, break_minutes=brk, phase="study", start_time=start, end_time=end, paused=False)
    with Session(engine) as db:
        db.add(p); db.commit(); db.refresh(p)
    return {"session_id": session_id, "client_id": client_id, "start_time": start.isoformat()+"Z", "end_time": end.isoformat()+"Z", "phase": "study"}

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    with Session(engine) as db:
        s = db.get(PomSession, session_id)
        if not s:
            raise HTTPException(404, "Session not found")
        return s

@app.post("/api/sessions/pause")
def pause_session(payload: dict):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    with Session(engine) as db:
        s = db.get(PomSession, session_id)
        if not s:
            raise HTTPException(404)
        if s.paused:
            return {"status": "already_paused"}
        now = datetime.utcnow()
        if s.end_time:
            remaining = int((s.end_time - now).total_seconds())
            s.remaining_seconds = max(0, remaining)
        s.paused = True
        s.paused_at = now
        db.add(s); db.commit(); db.refresh(s)
        return {"status": "paused", "remaining_seconds": s.remaining_seconds}

@app.post("/api/sessions/resume")
def resume_session(payload: dict):
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    with Session(engine) as db:
        s = db.get(PomSession, session_id)
        if not s:
            raise HTTPException(404)
        if not s.paused:
            return {"status": "already_running"}
        now = datetime.utcnow()
        rem = int(s.remaining_seconds or 0)
        s.end_time = now + timedelta(seconds=rem)
        s.paused = False
        s.paused_at = None
        s.remaining_seconds = None
        db.add(s); db.commit(); db.refresh(s)
        return {"status": "resumed", "end_time": s.end_time.isoformat()+"Z"}

@app.post("/api/sessions/reset")
def reset_session(payload: dict):
    session_id = payload.get("session_id")
    with Session(engine) as db:
        s = db.get(PomSession, session_id)
        if not s:
            raise HTTPException(404)
        s.phase = "idle"
        s.start_time = None
        s.end_time = None
        s.paused = False
        s.paused_at = None
        s.remaining_seconds = None
        db.add(s); db.commit();
        return {"status": "reset"}

@app.post("/api/sessions/skip")
def skip_session(payload: dict):
    session_id = payload.get("session_id")
    with Session(engine) as db:
        s = db.get(PomSession, session_id)
        if not s:
            raise HTTPException(404)
        # If in study, skip to break. If in break, end session.
        now = datetime.utcnow()
        if s.phase == "study":
            s.phase = "break"
            s.start_time = now
            s.end_time = now + timedelta(minutes=s.break_minutes)
        else:
            # finish
            s.phase = "idle"
            s.start_time = None
            s.end_time = None
        db.add(s); db.commit(); db.refresh(s)
        return {"status": "skipped", "phase": s.phase}

@app.post("/api/history/add")
def add_history(payload: dict):
    with Session(engine) as db:
        h = CompletedTask(
            client_id=payload.get("client_id"),
            task_text=payload.get("task_text"),
            study_duration_seconds=int(payload.get("study_duration_seconds",0)),
            break_duration_seconds=int(payload.get("break_duration_seconds",0)),
            completed_at=datetime.utcnow()
        )
        db.add(h); db.commit(); db.refresh(h)
        return {"id": h.id}

@app.get("/api/history")
def list_history():
    with Session(engine) as db:
        rows = db.exec(select(CompletedTask).order_by(CompletedTask.completed_at.desc())).all()
        return rows

@app.delete("/api/history/{history_id}")
def delete_history(history_id: int):
    with Session(engine) as db:
        h = db.get(CompletedTask, history_id)
        if not h:
            raise HTTPException(404)
        db.delete(h); db.commit()
        return {"status": "deleted"}

@app.post("/api/history/export")
def export_history():
    with Session(engine) as db:
        rows = db.exec(select(CompletedTask).order_by(CompletedTask.completed_at.desc())).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id","client_id","task_text","study_duration_seconds","break_duration_seconds","completed_at"])
        for r in rows:
            writer.writerow([r.id, r.client_id, r.task_text, r.study_duration_seconds, r.break_duration_seconds, r.completed_at.isoformat()+"Z"])
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=history.csv"})

@app.get("/api/wallpapers/random")
def random_wallpaper():
    with Session(engine) as db:
        w = db.exec(select(Wallpaper)).first()
        if not w:
            return {"url": None}
        return {"url": f"/wallpapers/{w.filename}", "filename": w.filename}
