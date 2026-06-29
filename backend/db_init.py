"""Database initialization helper
"""
from sqlmodel import SQLModel, create_engine
import os
from .models import Setting, Session, CompletedTask, Wallpaper

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./db.sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized at", DATABASE_URL)
