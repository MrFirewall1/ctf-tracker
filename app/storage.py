"""Lagring: én markdown-fil per oppgave med YAML-frontmatter. Filene er fasit."""
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import yaml

from .constants import CATEGORIES, DIFFICULTIES, PROTOCOLS, STATUSES

MARKER = ".ctf-tracker"
TASKS_DIR = "tasks"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,120}$")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.S)
FIELD_ORDER = [
    "title", "date", "source", "category", "protocol", "difficulty",
    "time_minutes", "tools", "tags", "status", "hints_used", "resolved_later",
]

GITIGNORE = """# PDF-rapporter, midlertidige filer og SQLite-indeks skal ikke i git
*.pdf
*.tmp
.*.tmp
*.sqlite
*.sqlite3
*.db
*.db-journal
reports/
.DS_Store
"""


class DataDirError(Exception):
    """Datamappen mangler, er ikke montert, ikke initialisert eller ikke skrivbar."""


# --- datamappe ---------------------------------------------------------------

def check_data_dir(path, writable: bool = True) -> Path:
    if not path:
        raise DataDirError(
            "Ingen datamappe er satt. Sett miljøvariabelen CTF_DATA_DIR eller "
            "data_dir i config.json til stien på SSD-en."
        )
    p = Path(path)
    if not p.exists():
        raise DataDirError(f"Datamappen finnes ikke: {p}. Er SSD-en koblet til og montert?")
    if not p.is_dir():
        raise DataDirError(f"Datamappen er ikke en mappe: {p}")
    if not (p / MARKER).is_file():
        raise DataDirError(
            f"{p} mangler filen {MARKER}. Enten er SSD-en ikke montert (tom monteringsmappe), "
            "eller mappen er ikke satt opp ennå. Kjør 'python -m app init' én gang."
        )
    if writable and not os.access(p, os.W_OK):
        raise DataDirError(f"Ingen skrivetilgang til {p}.")
    return p


def init_data_dir(path) -> Path:
    """Setter opp en EKSISTERENDE mappe. Oppretter aldri selve rotmappen."""
    if not path:
        raise DataDirError("Ingen datamappe er satt (CTF_DATA_DIR eller config.json).")
    p = Path(path)
    if not p.is_dir():
        raise DataDirError(
            f"Mappen finnes ikke: {p}. Monter SSD-en og opprett mappen selv først; "
            "appen oppretter ikke rotmappen for å unngå data på feil sted."
        )
    (p / TASKS_DIR).mkdir(exist_ok=True)
    if not (p / MARKER).exists():
        atomic_write_text(p / MARKER, "CTF-tracker datamappe. Ikke slett denne filen.\n")
    if not (p / ".gitignore").exists():
        atomic_write_text(p / ".gitignore", GITIGNORE)
    return p


# --- trygg skriving ----------------------------------------------------------

def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Skriv til midlertidig fil i samme mappe, fsync, og rename over målet."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    try:  # best effort: sørg for at selve rename-en når disken
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


# --- normalisering og (de)serialisering --------------------------------------

def _as_list(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        value = value.split(",")
    return [str(v).strip() for v in value if str(v).strip()]


def _as_int(value, name, errors) -> int:
    if value in (None, ""):
        return 0
    try:
        n = int(value)
    except (TypeError, ValueError):
        errors.append(f"{name} må være et heltall.")
        return 0
    if n < 0:
        errors.append(f"{name} kan ikke være negativ.")
        return 0
    return n


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "ja", "on", "yes")
    return bool(value)


def normalize_task(raw: dict) -> dict:
    """Validerer og renser en oppgave. Kaster ValueError med liste over feil."""
    errors: list[str] = []
    title = str(raw.get("title") or "").strip()
    if not title:
        errors.append("Tittel mangler.")

    d = raw.get("date")
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d.strip())
        except ValueError:
            d = None
    if not isinstance(d, date):
        errors.append("Dato må være på formen ÅÅÅÅ-MM-DD.")
        d = date.today()

    category = str(raw.get("category") or "").strip()
    if category not in CATEGORIES:
        errors.append("Ugyldig kategori.")
    protocol = str(raw.get("protocol") or "").strip()
    if protocol not in PROTOCOLS:
        errors.append("Ugyldig protokoll.")
    difficulty = str(raw.get("difficulty") or "").strip()
    if difficulty not in DIFFICULTIES:
        errors.append("Ugyldig vanskelighetsgrad.")
    status = str(raw.get("status") or "").strip()
    if status not in STATUSES:
        errors.append("Ugyldig status.")

    task = {
        "title": title,
        "date": d.isoformat(),
        "source": str(raw.get("source") or "").strip(),
        "category": category,
        "protocol": protocol,
        "difficulty": difficulty,
        "time_minutes": _as_int(raw.get("time_minutes"), "Tid brukt", errors),
        "tools": _as_list(raw.get("tools")),
        "tags": _as_list(raw.get("tags")),
        "status": status,
        "hints_used": _as_int(raw.get("hints_used"), "Antall hint", errors),
        "resolved_later": _as_bool(raw.get("resolved_later", False)),
        "body": str(raw.get("body") or "").replace("\r\n", "\n"),
    }
    if errors:
        raise ValueError("\n".join(errors))
    return task


def serialize_task(task: dict) -> str:
    meta = {k: task[k] for k in FIELD_ORDER}
    meta["date"] = date.fromisoformat(meta["date"])  # skrives uten anførselstegn
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=False)
    body = task.get("body", "").rstrip("\n")
    return f"---\n{front}---\n\n{body}\n"


def parse_task_file(text: str, task_id: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("Mangler YAML-frontmatter (--- ... ---).")
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        raise ValueError(f"Ugyldig YAML: {e}") from e
    if not isinstance(meta, dict):
        raise ValueError("Frontmatter må være en nøkkel/verdi-liste.")
    meta["body"] = m.group(2).lstrip("\n")
    task = normalize_task(meta)
    task["id"] = task_id
    return task


# --- id og filoperasjoner -----------------------------------------------------

def slugify(title: str) -> str:
    s = title.lower().replace("æ", "ae").replace("ø", "o").replace("å", "a")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60].strip("-") or "oppgave"


def _task_path(data_dir: Path, task_id: str) -> Path:
    if not ID_RE.match(task_id):
        raise ValueError("Ugyldig oppgave-id.")
    return data_dir / TASKS_DIR / f"{task_id}.md"


def list_tasks(data_dir) -> tuple[list[dict], list[dict]]:
    """Returnerer (oppgaver, feil). Ødelagte filer hoppes over og rapporteres."""
    p = check_data_dir(data_dir, writable=False)
    tasks, errors = [], []
    tdir = p / TASKS_DIR
    if not tdir.is_dir():
        return [], []
    for f in sorted(tdir.glob("*.md")):
        try:
            tasks.append(parse_task_file(f.read_text(encoding="utf-8"), f.stem))
        except (ValueError, OSError, UnicodeDecodeError) as e:
            errors.append({"file": f.name, "error": str(e)})
    tasks.sort(key=lambda t: (t["date"], t["id"]), reverse=True)
    return tasks, errors


def get_task(data_dir, task_id: str) -> dict:
    p = check_data_dir(data_dir, writable=False)
    path = _task_path(p, task_id)
    if not path.is_file():
        raise FileNotFoundError(task_id)
    return parse_task_file(path.read_text(encoding="utf-8"), task_id)


def save_task(data_dir, raw: dict, task_id: str | None = None) -> dict:
    """Oppretter (task_id=None) eller oppdaterer en oppgave. Sjekker SSD-en først."""
    p = check_data_dir(data_dir, writable=True)
    task = normalize_task(raw)
    tdir = p / TASKS_DIR
    if not tdir.is_dir():
        raise DataDirError(f"Mappen {tdir} mangler. Kjør 'python -m app init'.")
    if task_id is None:
        base = f"{task['date']}-{slugify(task['title'])}"
        task_id, n = base, 2
        while (tdir / f"{task_id}.md").exists():
            task_id, n = f"{base}-{n}", n + 1
    else:
        if not _task_path(p, task_id).is_file():
            raise FileNotFoundError(task_id)
    atomic_write_text(_task_path(p, task_id), serialize_task(task))
    task["id"] = task_id
    return task
