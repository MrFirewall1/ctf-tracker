"""Statistikk for dashboardet. Ren funksjon av oppgavelisten, lett å teste."""
from collections import defaultdict
from datetime import date, timedelta

from .constants import (
    CATEGORIES, MIN_SAMPLES_WEAK, PROTOCOLS, SOLVED_STATUSES, STATUSES,
)


def _d(task) -> date:
    return date.fromisoformat(task["date"])


def _week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-U{w:02d}"


def _weeks(first: date, last: date) -> list[str]:
    cur = first - timedelta(days=first.weekday())
    out = []
    while cur <= last:
        out.append(_week_key(cur))
        cur += timedelta(days=7)
    return out


def _has_learning(task) -> bool:
    """Er «Hva jeg lærte» faktisk fylt ut (ikke bare overskriften)?"""
    body = task.get("body", "")
    marker = "## Hva jeg lærte"
    if marker not in body:
        return False
    return bool(body.split(marker, 1)[1].split("\n## ", 1)[0].strip())


def _rate(solved: int, total: int):
    return round(solved / total, 4) if total else None


def _group_rates(tasks, field, labels):
    groups = defaultdict(lambda: [0, 0])
    for t in tasks:
        key = t[field]
        groups[key][0] += 1
        groups[key][1] += t["status"] in SOLVED_STATUSES
    rows = [
        {"key": k, "label": labels.get(k, k), "total": tot, "solved": sol, "rate": _rate(sol, tot)}
        for k, (tot, sol) in groups.items()
    ]
    rows.sort(key=lambda r: (-r["total"], r["label"]))
    return rows


def streaks(dates: set[date], today: date) -> tuple[int, int]:
    """(nåværende, lengste) rekke av dager med minst én oppgave."""
    if not dates:
        return 0, 0
    ordered = sorted(dates)
    longest = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)
    anchor = today if today in dates else today - timedelta(days=1)
    current = 0
    while anchor in dates:
        current += 1
        anchor -= timedelta(days=1)
    return current, longest


def compute_stats(tasks: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    total = len(tasks)
    solved = sum(t["status"] in SOLVED_STATUSES for t in tasks)
    status_counts = {k: 0 for k in STATUSES}
    for t in tasks:
        status_counts[t["status"]] += 1

    result = {
        "totals": {
            "tasks": total,
            "solved": solved,
            "rate": _rate(solved, total),
            "hints": sum(t["hints_used"] for t in tasks),
            "avg_hints": round(sum(t["hints_used"] for t in tasks) / total, 2) if total else None,
            "resolved_later": sum(t["resolved_later"] for t in tasks),
            "explained": sum(_has_learning(t) for t in tasks),
        },
        "status_share": [
            {"key": k, "label": STATUSES[k], "count": c} for k, c in status_counts.items()
        ],
        "by_category": _group_rates(tasks, "category", CATEGORIES),
        "by_protocol": _group_rates([t for t in tasks if t["protocol"]], "protocol", PROTOCOLS),
    }

    if not tasks:
        result.update(
            solved_over_time={"labels": [], "solved": [], "cumulative": []},
            hints_over_time={"labels": [], "avg_hints": []},
            sessions_per_week={"labels": [], "days": []},
            to_revisit=[],
            streak={"current": 0, "longest": 0},
            weakest=[],
        )
        return result

    first = min(_d(t) for t in tasks)
    last = max(max(_d(t) for t in tasks), today)

    weeks = _weeks(first, last)
    solved_by_week = defaultdict(int)
    days_by_week = defaultdict(set)
    for t in tasks:
        wk = _week_key(_d(t))
        days_by_week[wk].add(t["date"])
        if t["status"] in SOLVED_STATUSES:
            solved_by_week[wk] += 1
    per_week = [solved_by_week[w] for w in weeks]
    cumulative, acc = [], 0
    for n in per_week:
        acc += n
        cumulative.append(acc)
    result["solved_over_time"] = {"labels": weeks, "solved": per_week, "cumulative": cumulative}
    result["sessions_per_week"] = {"labels": weeks, "days": [len(days_by_week[w]) for w in weeks]}

    hints_by_week = defaultdict(list)
    for t in tasks:
        hints_by_week[_week_key(_d(t))].append(t["hints_used"])
    result["hints_over_time"] = {
        "labels": weeks,
        "avg_hints": [
            round(sum(hints_by_week[w]) / len(hints_by_week[w]), 2) if hints_by_week[w] else None
            for w in weeks
        ],
    }

    # Repetisjonsliste: ikke løst alene og ikke løst på nytt uten hjelp. Eldste først.
    revisit = [t for t in tasks if t["status"] != "solved_alone" and not t["resolved_later"]]
    revisit.sort(key=lambda t: (t["date"], t["id"]))
    result["to_revisit"] = [
        {"id": t["id"], "title": t["title"], "date": t["date"], "status": t["status"],
         "label": STATUSES[t["status"]]}
        for t in revisit[:8]
    ]

    current, longest = streaks({_d(t) for t in tasks}, today)
    result["streak"] = {"current": current, "longest": longest}

    weak = [
        {**r, "kind": "Kategori"} for r in result["by_category"]
    ] + [
        {**r, "kind": "Protokoll"} for r in result["by_protocol"]
    ]
    weak = [r for r in weak if r["total"] >= MIN_SAMPLES_WEAK and r["rate"] < 1.0]
    weak.sort(key=lambda r: (r["rate"], -r["total"]))
    result["weakest"] = weak[:5]
    return result
