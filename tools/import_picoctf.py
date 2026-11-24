"""Legger picoCTF-oppgaver (slik de står i Challenge Library hos Cylab Academy) inn i app/practice.json.

Kun tittel, forfatter, kategori, vanskelighet og arrangement. Ingen oppgavetekster, filer eller løsninger kopieres:
kortet lenker til biblioteket der du åpner oppgaven selv (krever konto). Kjøres på nytt uten duplikater.
    python -I tools/import_picoctf.py
"""
import json
import re
from pathlib import Path

PJ = Path(__file__).resolve().parent.parent / "app" / "practice.json"
URL = "https://learn.cylabacademy.org/library"
PREFIX = "pico-"
RE, GS, CR, WEB = "reversing", "other", "crypto", "web"
LABEL = {WEB: ("Web Exploitation", "Web-exploitation"), RE: ("Reverse Engineering", "Reverse engineering"), GS: ("General Skills", "General Skills"), CR: ("Cryptography", "Kryptografi")}

# (tittel, forfatter, kategori, vanskelighet, arrangement)
TASKS = [
    ("Insp3ct0r", "", WEB, "easy", "picoGym"), ("Cookies", "", WEB, "easy", "picoGym"),
    ("Flag Hunters", "syreal", RE, "easy", "picoCTF 2025"), ("Picker II", "LT 'syreal' Jones", RE, "easy", "picoCTF"),
    ("Picker I", "LT 'syreal' Jones", RE, "easy", "picoCTF"), ("GDB baby step 4", "LT 'syreal' Jones", RE, "easy", "picoCTF"),
    ("GDB baby step 3", "LT 'syreal' Jones", RE, "easy", "picoCTF"), ("GDB baby step 2", "LT 'syreal' Jones", RE, "easy", "picoCTF"),
    ("GDB baby step 1", "LT 'syreal' Jones", RE, "easy", "picoCTF"), ("Bit-O-Asm-4", "LT 'syreal' Jones", RE, "easy", "picoCTF"),
    ("Bit-O-Asm-3", "LT 'syreal' Jones", RE, "easy", "picoCTF"), ("Bit-O-Asm-2", "LT 'syreal' Jones", RE, "easy", "picoCTF"),
    ("Bit-O-Asm-1", "LT 'syreal' Jones", RE, "easy", "picoCTF"), ("ASCII FTW", "Abhishek Agarwal", RE, "easy", "picoCTF"),
    ("Transformation", "madStacks", RE, "easy", "picoCTF 2021"), ("vault-door-training", "Mark E. Haase", RE, "easy", "picoCTF 2019"),
    ("Secure Password Database", "Philip Thayer", RE, "medium", "picoCTF 2026"), ("Bypass Me", "Prince Niyonshuti N.", RE, "medium", "picoCTF 2026"),
    ("Autorev 1", "SkrubLawd", RE, "medium", "picoCTF 2026"), ("Hidden Cipher 2", "Yahaya Meddy", RE, "medium", "picoCTF 2026"),
    ("Hidden Cipher 1", "Yahaya Meddy", RE, "medium", "picoCTF 2026"), ("Gatekeeper", "Yahaya Meddy", RE, "medium", "picoCTF 2026"),
    ("Silent Stream", "Yahaya Meddy", RE, "medium", "picoCTF 2026"), ("The Add/On Trap", "Alessandro Greco aka Aleff", RE, "medium", "picoCTF 2026"),
    ("Pico Bank", "Prince Niyonshuti N.", RE, "medium", "picoMini by CMU-Africa"), ("M1n10n'5_53cr37", "Prince Niyonshuti N.", RE, "medium", "picoMini by CMU-Africa"),
    ("Undo", "Yahaya Meddy", GS, "easy", "picoCTF 2026"), ("MY GIT", "Darkraicg492", GS, "easy", "picoCTF 2026"),
    ("bytemancy 1", "LT 'syreal' Jones", GS, "easy", "picoCTF 2026"), ("Printer Shares", "Janice He", GS, "easy", "picoCTF 2026"),
    ("ping-cmd", "Yahaya Meddy", GS, "easy", "picoCTF 2026"), ("bytemancy 0", "LT 'syreal' Jones", GS, "easy", "picoCTF 2026"),
    ("Piece by Piece", "Yahaya Meddy", GS, "easy", "picoCTF 2026"), ("SUDO MAKE ME A SANDWICH", "Darkraicg492", GS, "easy", "picoCTF 2026"),
    ("Password Profiler", "Yahaya Meddy", GS, "easy", "picoCTF 2026"), ("MultiCode", "Yahaya Meddy", GS, "easy", "picoCTF 2026"),
    ("Log Hunt", "Yahaya Meddy", GS, "easy", "picoMini by CMU-Africa"), ("FANTASY CTF", "syreal", GS, "easy", "picoCTF 2025"),
    ("StegoRSA", "Yahaya Meddy", CR, "easy", "picoCTF 2026"), ("Shared Secrets", "Yahaya Meddy", CR, "easy", "picoCTF 2026"),
    ("hashcrack", "Nana Ama Atombo-Sackey", CR, "easy", "picoCTF 2025"), ("EVEN RSA CAN BE BROKEN???", "Michael Crotty", CR, "easy", "picoCTF 2025"),
    ("interencdec", "NGIRIMANA Schadrack", CR, "easy", "picoCTF 2024"), ("Mod 26", "Pandu", CR, "easy", "picoCTF 2021"),
    ("The Numbers", "Danny", CR, "easy", "picoCTF 2019"), ("13", "Alex Fulton/Daniel Tunitis", CR, "easy", "picoCTF 2019"),
    ("Timestamped Secrets", "Yahaya Meddy", CR, "medium", "picoCTF 2026"), ("Small Trouble", "Yahaya Meddy", CR, "medium", "picoCTF 2026"),
    ("shift registers", "Philip Thayer", CR, "medium", "picoCTF 2026"), ("Related Messages", "Philip Thayer", CR, "medium", "picoCTF 2026"),
    ("HideToSee", "Sunday Jacob Nwanyim", CR, "medium", "picoCTF 2023"), ("Vigenere", "Mubarak Mikail", CR, "medium", "picoCTF 2022"),
    ("transposition-trial", "Will Hong", CR, "medium", "picoCTF 2022"), ("substitution2", "Will Hong", CR, "medium", "picoCTF 2022"),
    ("substitution1", "Will Hong", CR, "medium", "picoCTF 2022"), ("substitution0", "Will Hong", CR, "medium", "picoCTF 2022"),
    ("rail-fence", "Will Hong", CR, "medium", "picoCTF 2022"), ("morse-code", "Will Hong", CR, "medium", "picoCTF 2022"),
    ("credstuff", "Will Hong / LT 'syreal' Jones", CR, "medium", "picoCTF 2022"), ("basic-mod2", "Will Hong", CR, "medium", "picoCTF 2022"),
    ("basic-mod1", "Will Hong", CR, "medium", "picoCTF 2022"), ("spelling-quiz", "BrownieInMotion", CR, "medium", "picoMini by redpwn"),
]

HINTS = {  # generelle råd per kategori, ikke spesifikke for oppgaven
    WEB: (["Open the browser's developer tools (F12) and look at the page source, the network tab and storage.",
           "Note what the server sends back and what the browser stores for you.",
           "Change one thing at a time and watch how the response changes."],
          ["Åpne utviklerverktøyene i nettleseren (F12) og se på sidekilden, nettverksfanen og lagring.",
           "Noter hva serveren sender tilbake og hva nettleseren lagrer for deg.",
           "Endre én ting om gangen og se hvordan svaret endrer seg."]),
    RE: (["Run the program first and note what it prints or asks for.",
          "Look at the strings or the disassembly to see what your input is compared against.",
          "Write down what each step does before you try to reverse it."],
         ["Kjør programmet først og noter hva det skriver ut eller spør om.",
          "Se på strengene eller disassemblyen for å finne hva inndataen sammenlignes med.",
          "Skriv ned hva hvert steg gjør før du prøver å snu det."]),
    GS: (["Read the task text twice and note exactly what you are asked to find.",
          "Try the terminal tools you know (ls, cat, grep, file) before anything fancy.",
          "man <command> or --help usually shows the option you need."],
         ["Les oppgaveteksten to ganger og noter nøyaktig hva du skal finne.",
          "Prøv terminalverktøyene du kan (ls, cat, grep, file) før noe avansert.",
          "man <kommando> eller --help viser som regel valget du trenger."]),
    CR: (["Work out what kind of cipher or encoding it is before you try to break it.",
          "Look for clues in the text about key size, alphabet or number of rounds.",
          "CyberChef or a few lines of Python are usually enough at this level."],
         ["Finn ut hva slags chiffer eller koding det er før du prøver å knekke det.",
          "Se etter spor i teksten om nøkkelstørrelse, alfabet eller antall runder.",
          "CyberChef eller noen linjer Python holder som regel på dette nivået."]),
}


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def entry(t):
    title, author, cat, diff, event = t
    en_cat, no_cat = LABEL[cat]
    en_h, no_h = HINTS[cat]
    return {
        "id": PREFIX + slug(title), "kind": "picoctf", "title": title,
        "source": " · ".join(x for x in ("picoCTF", event, author) if x),
        "url": "https://play.picoctf.org/practice" if event == "picoGym" else URL, "category": cat, "protocol": "", "difficulty": diff,
        "objective": f"A picoCTF challenge ({en_cat}, {event}). Open it " + ("in picoGym (play.picoctf.org, free account)" if event == "picoGym" else "in the Challenge Library on Cylab Academy (account needed)") + ", "
                     "read the task text there and solve it in your own terminal.",
        "hints": en_h, "tags": ["picoctf", cat],
        "no": {"title": title,
               "objective": f"En picoCTF-oppgave ({no_cat}, {event}). Åpne den "
                            + ("i picoGym (play.picoctf.org, gratis konto)" if event == "picoGym"
                               else "i Challenge Library hos Cylab Academy (krever konto)")
                            + ", les oppgaveteksten der og løs den i din egen terminal.",
               "hints": no_h},
    }


def main():
    old = json.loads(PJ.read_text(encoding="utf-8"))
    kept = [e for e in old if not e["id"].startswith(PREFIX)]
    new = [entry(t) for t in TASKS]
    assert len({e["id"] for e in new}) == len(new)
    PJ.write_text(json.dumps(kept + new, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Beholdt {len(kept)}, la inn {len(new)} picoCTF-oppgaver")


if __name__ == "__main__":
    main()
