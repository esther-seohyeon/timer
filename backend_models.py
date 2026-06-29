from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Setting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: Optional[str] = None
    default_study_minutes: int = 52
    default_break_minutes: int = 17
    wallpaper_rotation: bool = True
    airplane_reminders_on: bool = True

class Session(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    client_id: str
    task_text: Optional[str] = None
    study_minutes: int = 52
    break_minutes: int = 17
    phase: str = "idle"  # "study", "break", "idle"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    paused: bool = False
    paused_at: Optional[datetime] = None
    remaining_seconds: Optional[int] = None

class CompletedTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str
    task_text: str
    study_duration_seconds: int
    break_duration_seconds: int
    completed_at: datetime

class Wallpaper(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    sha256: str
    width: int
    height: int
    url_source: str
    downloaded_at: datetime