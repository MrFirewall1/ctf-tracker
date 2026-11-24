"""Videolenker per kategori (kun YouTube), lagret i datamappen som videos.json.

Appen laster ingenting selv: videoen hentes først når du trykker «Spill av» i nettleseren.
"""
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .constants import CATEGORIES
from .storage import atomic_write_text, check_data_dir

FILE = "videos.json"
ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
MAX_PER_CATEGORY = 20
MAX_MINUTES = 30   # lengre videoer godtas ikke


def parse_youtube(url: str) -> str | None:
    """11-tegns video-ID fra en YouTube-lenke, ellers None (ingen andre verter, ingen playlister uten video)."""
    try:
        u = urlparse((url or "").strip())
    except ValueError:
        return None
    if u.scheme not in ("http", "https") or (u.hostname or "").lower() not in HOSTS:
        return None
    host = u.hostname.lower()
    if host.endswith("youtu.be"):
        cand = u.path.lstrip("/").split("/")[0]
    elif u.path == "/watch":
        cand = (parse_qs(u.query).get("v") or [""])[0]
    else:
        parts = [x for x in u.path.split("/") if x]
        cand = parts[1] if len(parts) >= 2 and parts[0] in ("embed", "shorts", "live", "v") else ""
    return cand if ID_RE.fullmatch(cand or "") else None


def load(data_dir) -> dict:
    path = Path(data_dir) / FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for cat, items in (raw.items() if isinstance(raw, dict) else []):
        if cat in CATEGORIES and isinstance(items, list):
            out[cat] = [{"id": i["id"], "title": str(i.get("title", ""))[:120],
                         "minutes": i["minutes"] if isinstance(i.get("minutes"), int) and 1 <= i["minutes"] <= MAX_MINUTES else None}
                        for i in items
                        if isinstance(i, dict) and isinstance(i.get("id"), str) and ID_RE.fullmatch(i["id"])]
    return out


def _save(data_dir, data: dict) -> None:
    atomic_write_text(Path(data_dir) / FILE, json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def add(data_dir, category: str, url: str, title: str, minutes, allow_unknown: bool = False) -> dict:
    """Legg til en video. Kaster ValueError med norsk tekst ved ugyldig input."""
    if category not in CATEGORIES:
        raise ValueError("Ukjent kategori.")
    vid = parse_youtube(url)
    if not vid:
        raise ValueError("Det ser ikke ut som en YouTube-lenke (for eksempel https://www.youtube.com/watch?v=...).")
    if minutes is None and allow_unknown:      # kun for innlegging utenfra (ikke via API): lengden vises som «ikke sjekket»
        mins = None
    else:
        try:
            mins = int(str(minutes).strip())
        except ValueError:
            raise ValueError("Skriv inn lengden på videoen i hele minutter (se den under videoen på YouTube).") from None
        if not 1 <= mins <= MAX_MINUTES:
            raise ValueError(f"Videoer kan være maks {MAX_MINUTES} minutter. Finn en kortere.")
    check_data_dir(data_dir)
    data = load(data_dir)
    items = data.setdefault(category, [])
    if any(i["id"] == vid for i in items):
        raise ValueError("Videoen ligger allerede i denne kategorien.")
    if len(items) >= MAX_PER_CATEGORY:
        raise ValueError(f"Maks {MAX_PER_CATEGORY} videoer per kategori.")
    items.append({"id": vid, "title": (title or "").strip()[:120] or "Video", "minutes": mins})
    _save(data_dir, data)
    return data


def remove(data_dir, category: str, vid: str) -> dict:
    check_data_dir(data_dir)
    data = load(data_dir)
    data[category] = [i for i in data.get(category, []) if i["id"] != vid]
    if not data[category]:
        data.pop(category)
    _save(data_dir, data)
    return data
