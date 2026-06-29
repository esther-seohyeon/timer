import os
import hashlib
import io
from datetime import datetime
import requests
from PIL import Image
from sqlmodel import Session, select
from models import Wallpaper

# Example list of URLs (populate with actual page scraping or curated list)
SOURCES = [
    # Add a curated list of direct image URLs from the allowed site
]

DEST_DIR = "wallpapers"
os.makedirs(DEST_DIR, exist_ok=True)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def is_horizontal(img: Image.Image) -> bool:
    return img.width > img.height

def save_image(img: Image.Image, target_path: str):
    # Resize to max width = 1600, keeping aspect ratio
    max_w = 1600
    if img.width > max_w:
        h = int(max_w * img.height / img.width)
        img = img.resize((max_w, h), Image.LANCZOS)
    img.save(target_path, optimize=True, quality=85)

def fetch_and_store(db_session: Session, url: str):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        b = resp.content
        s = sha256_bytes(b)
        existing = db_session.exec(select(Wallpaper).where(Wallpaper.sha256 == s)).first()
        if existing:
            return existing
        img = Image.open(io.BytesIO(b)).convert("RGB")
        if not is_horizontal(img):
            return None
        filename = f"{s}.jpg"
        path = os.path.join(DEST_DIR, filename)
        save_image(img, path)
        wp = Wallpaper(filename=filename, sha256=s, width=img.width, height=img.height, url_source=url, downloaded_at=datetime.utcnow())
        db_session.add(wp)
        db_session.commit()
        return wp
    except Exception:
        return None

def run_fetch(db_engine):
    from sqlmodel import Session as DBSession
    with DBSession(db_engine) as db:
        for url in SOURCES:
            fetch_and_store(db, url)