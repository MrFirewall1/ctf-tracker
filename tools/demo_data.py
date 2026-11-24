"""Fyller en NY, tom datamappe med oppdiktede demodata, til skjermbilder og utprøving. Ingen ekte data.

    .venv/bin/python tools/demo_data.py /sti/til/ny-mappe

Mappen må ikke ha oppgaver fra før. Datoene settes relativt til i dag, så grafene alltid ser levende ut.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.storage import DataDirError, init_data_dir, list_tasks, save_task  # noqa: E402
from app.web import PRACTICE  # noqa: E402

A, H, S, U = "solved_alone", "solved_hint", "solved_solution", "unsolved"
# (id i katalogen, dager siden, status, hint brukt, minutter, verktøy, notat)
DEMO = [
    ("pico-insp3ct0r", 0, A, 0, 12, ["browser devtools"], "Åpnet kilden og leste gjennom alle filene."),
    ("lab-hidden-file", 1, A, 0, 8, ["ls", "find"], "Skjulte filer starter med punktum. Lærte å liste alt."),
    ("pico-mod-26", 2, A, 0, 10, ["CyberChef"], "Kjent rotasjonschiffer. Prøvde alle skift i CyberChef."),
    ("ics-fc-quiz", 3, A, 0, 15, ["Wireshark"], "Funksjonskodene for lesing og skriving satt ordentlig."),
    ("pico-cookies", 4, H, 1, 25, ["browser devtools", "curl"], "Brukte et hint om hvor cookien lagres."),
    ("labex-dir-traversal", 5, A, 0, 18, ["curl"], "../ i stien. Testet flere nivåer opp."),
    ("pico-hashcrack", 8, H, 1, 30, ["john", "CyberChef"], "Identifiserte hashtypen først. Hint om ordliste."),
    ("pico-13", 9, A, 0, 7, ["CyberChef"], "Rot13 i CyberChef."),
    ("labex-script-analysis", 12, H, 1, 35, ["cat", "python"], "Leste skriptet linje for linje. Hint om variabelen."),
    ("pico-gdb-baby-step-1", 13, S, 2, 50, ["gdb"], "Ble stående fast på breakpoints. Så løsningen, må øve mer."),
    ("lab-log-secret", 16, S, 2, 40, ["grep"], "Søkte feil i loggen. Så løsningen. Skal lære regulære uttrykk."),
    ("pico-bit-o-asm-1", 19, U, 3, 45, ["gdb", "objdump"], "Forsto ikke assembly ennå. Prøver igjen etter en intro."),
    ("lab-modbus-flag", 22, H, 1, 60, ["Wireshark", "tshark"], "Filtrerte på modbus og så på skriveforespørsler."),
    ("pico-log-hunt", 27, A, 0, 20, ["grep"], "grep med mønster, så lese rundt treffet."),
    ("pico-my-git", 31, A, 0, 22, ["git"], "Så på historikken og fant det som var slettet."),
    ("pico-interencdec", 35, A, 0, 14, ["CyberChef"], "Flere lag med koding. Pakket ut ett om gangen."),
    ("labex-log-secret", 41, U, 3, 40, ["grep", "less"], "Fant ikke hemmeligheten. Prøver på nytt med bedre søkeord."),
    ("pico-ascii-ftw", 48, A, 0, 16, ["python"], "Tegntabell og enkel dekoding."),
    ("ics-ot-modbus-lab01", 55, A, 0, 28, ["Wireshark"], "Baseline: hvem snakker med hvem, hvor ofte."),
    ("labex-web-input", 62, H, 1, 33, ["browser devtools"], "Skjemafelt og hva serveren stoler på."),
]


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    d = Path(argv[0]).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    init_data_dir(d)
    if list_tasks(d)[0]:
        print("Mappen har oppgaver fra før. Bruk en ny, tom mappe.")
        return 1
    today = date.today()
    n = 0
    for pid, ago, status, hints, minutes, tools, note in DEMO:
        e = PRACTICE.get(pid)
        if not e:
            continue
        body = ("## Hva spurte oppgaven om\n\n" + e["objective"].split("\n")[0][:300] +
                "\n\n## Min fremgangsmåte\n\n" + note + "\n\n## Kommandoer/filtre jeg brukte\n\n```\n" + ", ".join(tools) +
                "\n```\n\n## Hva som tok tid eller gikk galt\n\n" + ("Fikk hjelp av hint." if hints else "Gikk greit.") +
                "\n\n## Hva jeg lærte\n\n" + ("Må øve mer på dette." if status in (S, U) else "Teknikken sitter nå.") + "\n")
        save_task(d, {"title": e["title"], "date": (today - timedelta(days=ago)).isoformat(), "source": e["source"],
                      "category": e["category"], "protocol": e["protocol"], "difficulty": e["difficulty"],
                      "time_minutes": minutes, "tools": tools, "tags": e["tags"] + [f"practice-{pid}", "demo"],
                      "status": status, "hints_used": hints, "body": body})
        n += 1
    print(f"La inn {n} demo-oppgaver i {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
