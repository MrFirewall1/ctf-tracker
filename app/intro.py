"""Korte introer til hver kategori: hva det handler om, nøkkelbegreper og hvordan du kommer i gang.

Fast tekst skrevet på forhånd (ingen AI, ingen nett). Vises på dashboardet og på Oppvarming.
"""
import os

INTROS = {
    "pcap_ics": {
        "title": "PCAP / ICS (OT-nettverk)",
        "summary": ("Du får en nettverksfangst (PCAP) fra et industrielt anlegg (kraftverk, fabrikk, vannverk) og skal forklare hva "
                    "som skjedde: hvem snakker med hvem, hva er normalt, og hva er et angrep eller et skjult flagg. Du leser "
                    "pakker, du kjører ikke noe."),
        "terms": [
            ["PCAP / PCAPNG", "Fil med fangede nettverkspakker. Åpnes i Wireshark."],
            ["OT / ICS / SCADA", "Styringssystemer for fysiske prosesser. Oppetid og sikkerhet teller mer enn fortrolighet."],
            ["PLS / PLC", "Programmerbar logikkstyring: den lille datamaskinen som styrer ventiler, motorer og brytere."],
            ["HMI", "Skjermbildet operatøren ser og styrer anlegget fra."],
            ["Master / slave (klient / server)", "Masteren spør (poller), enheten svarer. Normal trafikk er jevn og repeterende."],
            ["Modbus/TCP", "Enkel og vanlig protokoll. Funksjonskode 1–4 leser, 5/6/15/16 skriver. Skriving fra ukjent kilde er mistenkelig."],
            ["DNP3, IEC-104, S7comm, GOOSE, EtherNet/IP", "Andre OT-protokoller (kraftnett, Siemens, stasjonsvern, Rockwell)."],
            ["Baseline", "Hvordan normal trafikk ser ut. Angrep ser du først når du kjenner baselinen."],
            ["Wireshark-filter", "For eksempel modbus, ip.src == 192.0.2.10, tcp.port == 502. Lær noen utenat."],
        ],
        "start": [
            "Åpne fangsten i Wireshark og se på Statistics → Protocol Hierarchy: hvilke protokoller finnes?",
            "Se på Statistics → Conversations: hvem snakker med hvem, og hvor mye?",
            "Finn baselinen først (normal polling), og let så etter det som avviker.",
        ],
        "tools": "Wireshark (Windows), tshark (WSL), valgfritt Pcapper.",
    },
    "web": {
        "title": "Web",
        "summary": ("Du angriper en nettside eller et API (lovlig, i en lab eller CTF) for å få tak i et flagg. Feilene handler "
                    "nesten alltid om at serveren stoler på det klienten sender."),
        "terms": [
            ["HTTP-forespørsel / -svar", "Metode (GET/POST), headere, cookies og body. Les dem i nettleserens utviklerverktøy."],
            ["Cookie / sesjon / JWT", "Slik nettstedet husker hvem du er. Kan ofte endres eller forfalskes ved svak signering."],
            ["SQL-injection", "Egen input havner i en databasespørring og endrer den."],
            ["XSS", "Egen input kjøres som JavaScript i en annen brukers nettleser."],
            ["Directory traversal", "../ i en filsti leser filer utenfor tiltenkt mappe."],
            ["IDOR", "Du bytter en id i URL-en og ser andres data."],
            ["SSRF", "Du får serveren til å hente en adresse for deg, ofte internt."],
            ["robots.txt, kildekode, skjulte felt", "Første steg: se hva siden selv avslører."],
        ],
        "start": [
            "Åpne siden, og se på kildekode og nettverksfanen i utviklerverktøyene.",
            "Finn alle steder du kan sende input (skjema, URL-parametere, cookies, headere).",
            "Test ett sted om gangen, og noter hva som endrer seg.",
        ],
        "tools": "Nettleserens utviklerverktøy, curl, Burp Suite Community.",
    },
    "crypto": {
        "title": "Krypto",
        "summary": ("Du får kryptert eller kodet tekst og skal komme fram til klarteksten. I CTF handler det sjelden om å knekke "
                    "sterk kryptering, men om en feil i hvordan den er brukt."),
        "terms": [
            ["Koding vs. kryptering", "Base64, hex og URL-koding er ikke kryptering: de kan snus uten nøkkel."],
            ["Klartekst / chiffertekst / nøkkel", "Før, etter og hemmeligheten som skiller dem."],
            ["Symmetrisk / asymmetrisk", "Samme nøkkel til begge (AES) eller offentlig/privat nøkkelpar (RSA)."],
            ["Hash", "Énveis fingeravtrykk (MD5, SHA-256). Svake hasher knekkes med ordlister."],
            ["XOR", "Enkel operasjon som går igjen. XOR to ganger med samme nøkkel gir tilbake originalen."],
            ["Caesar / Vigenère", "Klassiske chiffer. Frekvensanalyse knekker dem."],
            ["RSA: n, e, d, p, q", "Svake eller små primtall gjør det mulig å faktorisere n."],
        ],
        "start": [
            "Se på formatet: hex, base64, bare bokstaver, lange tall?",
            "Prøv enkel dekoding først (CyberChef), før du tenker på angrep.",
            "Spør: hva er feilen i bruken, ikke algoritmen?",
        ],
        "tools": "CyberChef, Python (pycryptodome), hashcat/john for hasher.",
    },
    "reversing": {
        "title": "Reversing (reverse engineering)",
        "summary": ("Du får et program uten kildekode og skal forstå hva det gjør, ofte for å finne riktig input eller flagget som "
                    "er gjemt i det. Du leser oppførsel, ikke bare kode."),
        "terms": [
            ["Binærfil / ELF / EXE", "Ferdig kompilert program (ELF på Linux, EXE på Windows)."],
            ["Disassembler / dekompilator", "Viser maskinkode som assembly eller C-lignende kode (Ghidra)."],
            ["Strings", "Lesbare tekster i filen. Ofte det første å sjekke."],
            ["Debugger", "Kjører programmet steg for steg og viser registre og minne (gdb)."],
            ["Statisk vs. dynamisk analyse", "Lese uten å kjøre, eller kjøre og observere."],
            ["Obfuskering / packing", "Koden er gjort vanskelig å lese med vilje."],
            ["Sjekk-funksjon", "Der programmet sammenligner din input med riktig svar."],
        ],
        "start": [
            "Kjør file og strings på binærfilen. Kjør den kun i en isolert VM, aldri på hovedmaskinen.",
            "Åpne i Ghidra, og finn main og funksjonen som sjekker input.",
            "Forstå logikken, og regn ut eller omgå sjekken.",
        ],
        "tools": "file, strings, Ghidra, gdb, objdump.",
    },
    "forensics": {
        "title": "Forensics",
        "summary": ("Du undersøker data etter en hendelse: filer, disker, minnedump, logger, bilder, e-poster. Flagget ligger skjult "
                    "eller slettet, og du må finne det fra sporene."),
        "terms": [
            ["Metadata (EXIF)", "Skjult info i filer: tid, forfatter, posisjon."],
            ["Magic bytes", "De første bytene som viser den virkelige filtypen, uansett filendelse."],
            ["Steganografi", "Data skjult inni et bilde eller en lydfil."],
            ["Diskavbilde / minnedump", "Kopi av en disk eller RAM som analyseres uten å endre originalen."],
            ["Logger", "Tidsstemplede hendelser: se etter mønstre og avvik."],
            ["Tidslinje", "Sett hendelser i rekkefølge for å forstå forløpet."],
            ["Hash av bevis", "Sjekksum som viser at filen ikke er endret."],
        ],
        "start": [
            "Ta en hash av filen, og kjør file, strings og exiftool.",
            "Se etter innebygde filer (binwalk) og uvanlige områder.",
            "Skriv ned hver observasjon og kilden til den, som en tidslinje.",
        ],
        "tools": "file, strings, exiftool, binwalk, Volatility, Autopsy.",
    },
    "other": {
        "title": "Annet",
        "summary": ("Oppgaver som ikke passer en kategori: Linux-ferdigheter, skript, gåter, OSINT og blandede CTF-oppgaver. "
                    "Øvelse i å angripe et problem systematisk."),
        "terms": [
            ["Linux-terminal", "ls -a, cat, grep, find, chmod, env. De fleste lette oppgaver løses her."],
            ["Skjulte filer", "Navn som starter med punktum vises ikke uten ls -a."],
            ["Miljøvariabler", "Prosesser kan ha hemmeligheter i environ (/proc/<pid>/environ)."],
            ["Rettigheter", "Hvem kan lese og skrive en fil (chmod, ls -l)."],
            ["OSINT", "Åpne kilder: finn informasjon som er offentlig tilgjengelig."],
        ],
        "start": [
            "Les oppgaveteksten to ganger, og noter hva som er gitt og hva som skal finnes.",
            "Start enkelt: se på filer, tekst og kommandoutdata før du prøver noe avansert.",
            "Skriv ned det du prøver. Det blir forklaringen din etterpå.",
        ],
        "tools": "Terminalen, grep, find, CyberChef.",
    },
}

HOW_TO_OPEN = [
    "Finn «Filer» på kortet: det er PCAP-ene oppgaven bruker. En grønn hake betyr at filen er lastet ned.",
    "Wireshark (Windows): File → Open, og lim inn Windows-stien fra kortet (for eksempel D:\\ctf-downloads\\…).",
    "Terminal (WSL): kopier tshark-kommandoen fra kortet, for eksempel for en rask oversikt over protokollene.",
    "Står det «ikke lastet ned ennå», kjør kommandoen under «Data» fra repoet ~/ctf-downloads/ICS-PCAP-Challenges.",
    "Les oppgaveteksten og målene, og prøv først uten hint. Åpner du et hint, noter det og logg det som brukt hint.",
]


def _windows_path(p: str) -> str | None:
    """/mnt/d/a/b -> D:\\a\\b (kun for drvfs-stier)."""
    parts = p.split("/")
    if len(parts) > 3 and parts[1] == "mnt" and len(parts[2]) == 1 and parts[2].isalpha():
        return parts[2].upper() + ":\\" + "\\".join(parts[3:])
    return None


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def safe_download_path(downloads_dir: str | None, rel: str) -> str | None:
    """Full sti til en fil INNE I nedlastingsmappen, ellers None (ingen ../, ingen lenker ut)."""
    if not downloads_dir or not rel:
        return None
    base = os.path.realpath(downloads_dir)
    full = os.path.realpath(os.path.join(base, rel))
    if os.path.commonpath([base, full]) != base or not os.path.isfile(full):
        return None
    return full


def file_info(downloads_dir: str | None, rel_files: list[str]) -> list[dict]:
    """For hver fil: stier og om den finnes. Tåler at disken mangler."""
    out = []
    for rel in rel_files:
        rel = rel[5:] if rel.startswith("data/") else rel
        item = {"rel": rel, "wsl": None, "win": None, "exists": None, "size": None}
        if downloads_dir:
            wsl = downloads_dir.rstrip("/") + "/" + rel
            item["wsl"], item["win"] = wsl, _windows_path(wsl)
            try:
                item["exists"] = os.path.isfile(wsl)
                if item["exists"]:
                    item["size"] = human_size(os.path.getsize(wsl))
            except OSError:
                item["exists"] = None
        out.append(item)
    return out


def readiness(fileinfo: list[dict]) -> str:
    """ready = alle filer finnes; partial = noen; missing = ingen; nofiles = oppgaven trenger ingen nedlastede filer;
    unknown = nedlastingsmappen er ikke satt/ikke tilgjengelig."""
    if not fileinfo:
        return "nofiles"
    states = [f["exists"] for f in fileinfo]
    if any(x is None for x in states):
        return "unknown"
    have = sum(1 for x in states if x)
    return "ready" if have == len(states) else ("partial" if have else "missing")


def catalog_summary(entries: list[dict], logged: set[str], flt: dict) -> dict:
    """Tall for dashboardet: hvor mange oppgaver finnes, hvor mange er klare (filer lastet ned) og hvor mange er logget.
    `entries` har allerede feltet `ready` (se readiness)."""
    rows = {}
    for e in entries:
        if any(flt.get(k) and e.get(k) != flt[k] for k in ("category", "difficulty", "protocol")):
            continue
        r = rows.setdefault(e["difficulty"], {"total": 0, "ready": 0, "partial": 0, "missing": 0, "logged": 0})
        r["total"] += 1
        key = e["ready"]
        if key in ("ready", "nofiles"):
            r["ready"] += 1
        elif key in ("partial", "missing"):
            r[key] += 1
        if e["id"] in logged:
            r["logged"] += 1
    total = {k: sum(r[k] for r in rows.values()) for k in ("total", "ready", "partial", "missing", "logged")}
    return {"by_difficulty": rows, "total": total}


# --- Oppvarming: to nybegynneroppgaver, ikoner, startveiledning og kalenderpåminnelse -------------------------------
# To oppvarmingsoppgaver per kategori: først en enkel, så en mer praktisk. Der det går brukes egne øvelser (svar kan sjekkes i appen).
WARMUP_TASKS = {
    "pcap_ics": ["ics-fc-quiz", "lab-modbus-flag"],
    "web": ["pico-insp3ct0r", "pico-cookies"],
    "crypto": ["pico-mod-26", "pico-hashcrack"],
    "reversing": ["pico-gdb-baby-step-1", "pico-bit-o-asm-1"],
    "forensics": ["lab-log-secret", "labex-log-secret"],
    "other": ["pico-log-hunt", "pico-my-git"],
}

# Enkle linjeikoner (innholdet i en 24x24 <svg>), ett per kategori. Statiske, ingen nett.
CATEGORY_ICONS = {
    "pcap_ics": '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
    "web": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    "crypto": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "reversing": '<path d="M8 8l-5 4 5 4M16 8l5 4-5 4M14 5l-4 14"/>',
    "forensics": '<circle cx="10" cy="10" r="6"/><path d="M15 15l6 6"/>',
    "other": '<path d="M12 3l2.5 5.5L20 9l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.5z"/>',
}

WEEKDAYS = [("MO", "Man"), ("TU", "Tir"), ("WE", "Ons"), ("TH", "Tor"), ("FR", "Fre"), ("SA", "Lør"), ("SU", "Søn")]

GENERATE_STEP = ("Lag øvelsene én gang (kjør i WSL-terminalen, utenfor datamappen): "
                 "cd ~/ctf-tracker && .venv/bin/python -m labs generate ~/ctf-labs")

BEGINNER_STEPS = {
    "lab-hidden-file": [
        GENERATE_STEP,
        "Gå inn i øvelsen: cd ~/ctf-labs/hidden-file",
        "Se deg rundt. Vanlig ls viser ikke alt, så finn ut hvordan du lister også skjulte filer (navn som starter med punktum).",
        "Flagget har formatet CTF{...}. Les filene du finner til du ser det.",
        "Sjekk svaret: .venv/bin/python -m labs check ~/ctf-labs hidden-file 'CTF{...}'",
        "Trykk «Logg denne» og skriv med egne ord hva du prøvde og hva som tok tid.",
    ],
    "lab-log-secret": [
        GENERATE_STEP,
        "Gå inn i øvelsen: cd ~/ctf-labs/log-secret",
        "Loggen er lang. Ikke les den linje for linje: bruk et søkeverktøy (grep) på noe du vet om flagget, for eksempel CTF.",
        "Det kan være flere treff som ser like ut. Les rundt treffet for å se hvilket som hører til oppgaven.",
        "Sjekk svaret: .venv/bin/python -m labs check ~/ctf-labs log-secret 'CTF{...}'",
        "Trykk «Logg denne» og skriv hva du søkte på og hvorfor.",
    ],
}


def start_steps(entry: dict, fileinfo: list[dict]) -> list[str]:
    """«Slik starter du»: konkrete steg for å komme i gang. Ingen løsninger, bare oppsett og fremgangsmåte."""
    if entry["id"] in BEGINNER_STEPS:
        return BEGINNER_STEPS[entry["id"]]
    if entry["id"].startswith("lab-"):
        lab = entry["id"][4:]
        return [GENERATE_STEP, f"Gå inn i øvelsen: cd ~/ctf-labs/{lab}",
                "Les oppgaveteksten og se hva som ligger i mappen.",
                f"Sjekk svaret: .venv/bin/python -m labs check ~/ctf-labs {lab} 'CTF{{...}}'",
                "Logg oppgaven når du er ferdig."]
    if entry.get("kind") == "picoctf":
        site = ("Logg inn på picoGym (play.picoctf.org, gratis konto) og gå til Practice (lenken «Åpne oppgaven på nettet» på kortet)."
                if "play.picoctf.org" in entry.get("url", "") else
                "Logg inn på Cylab Academy og åpne Challenge Library (lenken «Åpne oppgaven på nettet» på kortet).")
        return [site,
                f"Velg riktig kategori i filteret og søk etter «{entry['title']}».",
                "Åpne oppgaven, les teksten og last ned eventuelle filer eller start oppgavens instans.",
                "Jobb i terminalen i WSL eller Kali. Lag en egen mappe for oppgaven og legg filene der.",
                "Prøv uten hint. Åpner du et hint, noter det og logg det som brukt hint.",
                "Lever flagget på siden, og logg oppgaven her når du er ferdig."]
    if entry.get("data"):
        first = next((f for f in fileinfo if f.get("wsl")), None)
        steps = ["Last ned filen med «Last ned»-lenken under «Åpne oppgaven (filer)», eller bruk stien rett fra kortet."]
        if first:
            steps.append(f"Åpne i Wireshark: File → Open → {first['win'] or first['wsl']}")
            steps.append(f"Eller få en rask oversikt i WSL: tshark -r '{first['wsl']}' -q -z io,phs")
        else:
            steps.append("Åpne PCAP-filen i Wireshark (File → Open) og se på Statistics → Protocol Hierarchy.")
        steps += ["Les oppgaveteksten og målene. Lag deg en liste over hva du må finne.",
                  "Finn baselinen (normal trafikk) først, og let så etter avvik.",
                  "Prøv uten hint. Åpner du et hint, noter det og logg det som brukt hint."]
        return steps
    return ["Les oppgaveteksten to ganger og noter hva som er gitt og hva som skal finnes.",
            "Start i terminalen i WSL (eller i Kali). Lag en egen mappe for oppgaven og jobb der.",
            "Skriv ned kommandoene du prøver, de blir forklaringen din etterpå.",
            "Prøv uten hint. Åpner du et hint, noter det og logg det som brukt hint."]


def reminder_ics(time: str, days: list[str], text: str, today=None) -> str | None:
    """Gjentakende kalenderhendelse (iCalendar) med varsel. None hvis input er ugyldig."""
    import re
    from datetime import date
    m = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", time or "")
    valid = {d for d, _ in WEEKDAYS}
    days = [d for d in (days or []) if d in valid] if days else [d for d, _ in WEEKDAYS]
    if not m or not days:
        return None
    clean = re.sub(r"[^\wæøåÆØÅ .,!?:\-]", "", text or "")[:80] or "Tid for CTF-trening"
    day = (today or date.today()).strftime("%Y%m%d")
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ctf-tracker//reminder//NO", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT", f"UID:ctf-paminnelse-{day}-{m.group(1)}{m.group(2)}@ctf-tracker.local",
        f"DTSTAMP:{day}T000000Z", f"DTSTART:{day}T{m.group(1)}{m.group(2)}00", "DURATION:PT30M",
        "RRULE:FREQ=WEEKLY;BYDAY=" + ",".join(days), f"SUMMARY:{clean}",
        "DESCRIPTION:Logg minst én oppgave i ctf-tracker i dag.",
        "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{clean}", "TRIGGER:PT0M", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR", ""])
