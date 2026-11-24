"""XP, nivå, streak og aktivitetskart. Ren funksjon av oppgavelisten (ingen nett, ingen AI).

XP for en logget oppgave = vanskelighetspoeng x faktor for hvor selvstendig du løste den.
Løst alene gir full pott, hint gir mindre, fasit gir nesten ingenting (du lærte mindre), ikke løst gir 0.
"""
from collections import defaultdict
from datetime import date, timedelta

from .constants import CATEGORIES
from .stats import streaks

BASE = {"easy": 10, "medium": 25, "hard": 50}
FACTOR = {"solved_alone": 1.0, "solved_hint": 0.7, "solved_solution": 0.2, "unsolved": 0.0}
LEVELS = [(0, "Nybegynner"), (100, "Lærling"), (250, "Junior"), (500, "Medior"),
          (900, "Senior"), (1400, "Ekspert"), (2000, "Mester"), (3000, "Legende")]


def task_xp(task: dict) -> int:
    return round(BASE.get(task.get("difficulty"), 0) * FACTOR.get(task.get("status"), 0))


def level_for(xp: int) -> dict:
    idx = max(i for i, (need, _) in enumerate(LEVELS) if xp >= need)
    cur_need, name = LEVELS[idx]
    nxt = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None
    return {
        "name": name, "number": idx + 1, "from": cur_need,
        "next_name": nxt[1] if nxt else None, "next_at": nxt[0] if nxt else None,
        "to_next": (nxt[0] - xp) if nxt else 0,
        "progress": round((xp - cur_need) / (nxt[0] - cur_need), 3) if nxt else 1.0,
    }


def compute_xp(tasks: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    total = 0
    per_cat = defaultdict(int)
    per_day = defaultdict(int)
    week_xp = week_solved = 0
    days = set()
    for t in tasks:
        try:
            d = date.fromisoformat(t["date"])
        except (KeyError, ValueError):
            continue
        x = task_xp(t)
        total += x
        per_cat[t.get("category", "other")] += x
        per_day[d] += 1
        days.add(d)
        if 0 <= (today - d).days < 7:
            week_xp += x
            week_solved += 1 if x > 0 else 0
    current, longest = streaks(days, today)
    # Aktivitetskart: 53 uker x 7 dager, slutter på dagens uke (mandag først)
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=52)
    heat = [{"date": (start + timedelta(days=i)).isoformat(),
             "n": per_day.get(start + timedelta(days=i), 0)}
            for i in range(53 * 7) if start + timedelta(days=i) <= today]
    return {
        "xp": total, "level": level_for(total),
        "week_xp": week_xp, "week_solved": week_solved,
        "streak": {"current": current, "longest": longest},
        "active_days": len([d for d in days if (today - d).days < 365]),
        "heatmap": heat,
        "skills": [{"key": k, "label": CATEGORIES[k], "xp": per_cat.get(k, 0)} for k in CATEGORIES],
    }
