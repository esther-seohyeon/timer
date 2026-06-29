import os
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, create_engine, Session, select
from models import Setting, Session as PomSession, CompletedTask, Wallpaper
from wallpaper_downloader import run_fetch

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./db.sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

app = FastAPI(title="Pomodoro Study App")

# Serve static frontend build
app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")
app.mount("/wallpapers", StaticFiles(directory="wallpapers"), name="wallpapers")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    # Kick off wallpaper fetching in background
    # NOTE: keep this light; fetch only a few initial images
    BackgroundTasks().add_task(run_fetch, engine)

def get_settings_for_client(client_id: str):
    with Session(engine) as db:
        s = db.exec(select(Setting).where(Setting.client_id == client_id)).first()
        if not s:
            s = Setting(client_id=client_id)
            db.add(s); db.commit(); db.refresh(s)
        return s

@app.post("/api/sessions/start")
def start_session(payload: dict):
    # payload: client_id, task_text, study_minutes, break_minutes
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
    session_id = payload["session_id"]
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
    session_id = payload["session_id"]
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

@app.get("/api/wallpapers/random")
def random_wallpaper():
    with Session(engine) as db:
        w = db.exec(select(Wallpaper)).first()
        # For true randomness choose random row; simplified here:
        if not w:
            return {"url": None}
        return {"url": f"/wallpapers/{w.filename}", "filename": w.filename}