"""Finner datamappen. Prioritet: miljøvariabelen CTF_DATA_DIR, deretter config.json.

Det finnes bevisst ingen standardverdi: uten konfigurasjon nekter appen å skrive.
"""
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def config_file() -> Path:
    return Path(os.environ.get("CTF_CONFIG", PROJECT_ROOT / "config.json"))


def get_data_dir() -> str | None:
    env = os.environ.get("CTF_DATA_DIR")
    if env:
        return os.path.expanduser(env)
    cfg = config_file()
    if cfg.is_file():
        try:
            value = json.loads(cfg.read_text(encoding="utf-8")).get("data_dir")
        except (OSError, ValueError):
            return None
        if value:
            return os.path.expanduser(value)
    return None


def get_downloads_dir() -> str | None:
    """Mappen med nedlastede PCAP-er (CTF_DOWNLOADS_DIR eller `downloads_dir` i config.json). Valgfri, kun for visning."""
    env = os.environ.get("CTF_DOWNLOADS_DIR")
    if env:
        return os.path.expanduser(env)
    cfg = config_file()
    if cfg.is_file():
        try:
            value = json.loads(cfg.read_text(encoding="utf-8")).get("downloads_dir")
        except (OSError, ValueError):
            return None
        if value:
            return os.path.expanduser(value)
    return None


def get_labs_dir() -> str:
    """Mappen med egne øvelser (labs generate). CTF_LABS_DIR, `labs_dir` i config.json, ellers ~/ctf-labs."""
    env = os.environ.get("CTF_LABS_DIR")
    if env:
        return os.path.expanduser(env)
    cfg = config_file()
    if cfg.is_file():
        try:
            value = json.loads(cfg.read_text(encoding="utf-8")).get("labs_dir")
        except (OSError, ValueError):
            value = None
        if value:
            return os.path.expanduser(value)
    return os.path.expanduser("~/ctf-labs")
