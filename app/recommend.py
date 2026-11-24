"""Personlig anbefaling: hvilket område sliter du mest med, og hvilken oppgave bør du ta neste gang?

Ren funksjon av loggene dine (ingen nett, ingen AI). Samme regel som «Svakeste områder» på dashbordet:
kategorier med minst MIN_SAMPLES loggede oppgaver og løsningsrate under 100 % kommer først (lavest rate først),
deretter kategorier du knapt har prøvd.
"""
from .constants import CATEGORIES, MIN_SAMPLES_WEAK, SOLVED_STATUSES

ORDER = ("easy", "medium", "hard")


def weak_categories(tasks: list[dict]) -> list[dict]:
    stat = {k: [0, 0] for k in CATEGORIES}                   # [totalt, løst]
    for t in tasks:
        if t.get("category") in stat:
            stat[t["category"]][0] += 1
            stat[t["category"]][1] += t.get("status") in SOLVED_STATUSES
    weak, untried = [], []
    for key, (total, solved) in stat.items():
        if total >= MIN_SAMPLES_WEAK:
            if solved < total:
                weak.append((solved / total, key, f"løsningsrate {round(100 * solved / total)} % ({solved}/{total})"))
        else:
            untried.append((total, key, "ikke prøvd ennå" if total == 0 else f"bare {total} logget"))
    weak.sort()
    untried.sort()
    return [{"key": k, "label": CATEGORIES[k], "reason": r} for _, k, r in weak + untried]


def next_task(entries, logged_ids: set, category: str, is_ready=lambda e: True):
    """Første ulogget, klar oppgave i kategorien: lett før middels før vanskelig."""
    for diff in ORDER:
        for e in entries:
            if e["category"] == category and e["difficulty"] == diff and e["id"] not in logged_ids and is_ready(e):
                return e
    return None


def recommend(tasks, entries, logged_ids, is_ready=lambda e: True):
    """Anbefalt neste oppgave i det svakeste området som har noe å gi. None hvis alt er tatt."""
    for w in weak_categories(tasks):
        e = next_task(entries, logged_ids, w["key"], is_ready)
        if e:
            return {"category": w, "entry": e}
    return None
