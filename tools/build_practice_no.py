"""Gjør app/practice.json tospråklig: grunnfeltene (title/objective/hints) er engelske, og `no` har norsk.

Kjøres én gang etter import (idempotent). Ingen nettverk og ingen modell: oversettelsene er laget på forhånd
(tools/translations_no.json + faste regler i tools/translate_templates.py).
    python -I tools/build_practice_no.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from translate_templates import translate_all  # noqa: E402

PJ = HERE.parent / "app" / "practice.json"
MANUAL = json.loads((HERE / "translations_no.json").read_text(encoding="utf-8"))
ORIG_EN = json.loads((HERE / "original_en.json").read_text(encoding="utf-8"))


def tr(s: str) -> str:
    s = s.strip()
    return MANUAL.get(s) or translate_all(s) or s


def tr_objective(obj: str) -> str:
    scen, _, goals = obj.partition("\n\nMål: ")
    out = tr(scen)
    if goals:
        parts = [g for g in re.split(r" ?\(\d+\) ", goals) if g]
        out += "\n\nMål: " + " ".join(f"({i}) {tr(g)}" for i, g in enumerate(parts, 1))
    return out


def main():
    entries = json.loads(PJ.read_text(encoding="utf-8"))
    for e in entries:
        if "no" in e:
            continue
        if e["id"] in ORIG_EN:                       # opprinnelig norsk -> norsk går til `no`, engelsk blir grunnfelt
            en = ORIG_EN[e["id"]]
            e["no"] = {"title": e["title"], "objective": e["objective"], "hints": e["hints"]}
            e.update(title=en["title"], objective=en["objective"], hints=en["hints"])
        else:                                        # importert: engelsk fra før, lag norsk
            e["objective"] = e["objective"].replace("\n\nMål: ", "\n\nGoals: ", 1)
            e["objective"] = re.sub(r"^(.*\n\nGoals: )(.*)$", lambda m: m.group(1) + m.group(2), e["objective"], flags=re.S)
            e["no"] = {"title": tr(e["title"]), "objective": None, "hints": [tr(h) for h in e["hints"]]}
            e["no"]["objective"] = tr_objective(e["objective"].replace("\n\nGoals: ", "\n\nMål: ", 1))
    PJ.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    same = sum(1 for e in entries if e["no"]["objective"] == e["objective"])
    print(f"{len(entries)} oppføringer; {same} med uendret (engelsk) objective-tekst i no")


if __name__ == "__main__":
    main()
