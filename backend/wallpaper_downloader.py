import os
import io
import hashlib
from datetime import datetime
import time
import requests
from PIL import Image
from sqlmodel import Session, select
from .models import Wallpaper

# Fill this list with direct image URLs from the allowed site
SOURCES = [
    # Example: "https://ahomeisannounced.com/wp-content/uploads/2020/01/some-image.jpg",
]

DEST_DIR = os.path.join(os.path.dirname(__file__), "..", "wallpapers")
os.makedirs(DEST_DIR, exist_ok=True)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def is_horizontal(img: Image.Image) -> bool:
    return img.width > img.height


def save_image(img: Image.Image, target_path: str):
    max_w = int(os.environ.get("WALLPAPER_MAX_WIDTH", "1400"))
    if img.width > max_w:
        h = int(max_w * img.height / img.width)
        img = img.resize((max_w, h), Image.LANCZOS)
    img.save(target_path, format="JPEG", optimize=True, quality=80)


def fetch_and_store(db_session: Session, url: str):
    try:
        resp = requests.get(url, timeout=20)
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
    except Exception as e:
        # keep downloader resilient
        print("wallpaper fetch error", e)
        return None


def run_fetch(db_engine, limit: int = 20, delay: float = 1.0):
    """Conservative fetch: single-threaded, capped by limit, small delay between requests.
    db_engine: SQLModel/SQLAlchemy engine
    limit: max images to fetch
    delay: seconds between requests
    """
    from sqlmodel import Session as DBSession
    if not SOURCES:
        print("No wallpaper SOURCES configured. Populate wallpaper_downloader.SOURCES with approved image URLs.")
        return
    with DBSession(db_engine) as db:
        count = 0
        for url in SOURCES:
            if count >= limit:
                break
            try:
                res = fetch_and_store(db, url)
                if res:
                    count += 1
            except Exception as e:
                print("fetch loop error", e)
            time.sleep(delay)
        print(f"wallpaper fetch complete, fetched={count}")
