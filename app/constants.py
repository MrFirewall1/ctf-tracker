"""Faste verdier og norske visningsnavn. Nøklene lagres i filene, etikettene vises i UI."""

CATEGORIES = {
    "pcap_ics": "PCAP/ICS",
    "web": "Web",
    "crypto": "Krypto",
    "reversing": "Reversing",
    "forensics": "Forensics",
    "other": "Annet",
}

PROTOCOLS = {
    "": "Ingen / ikke relevant",
    "modbus": "Modbus",
    "dnp3": "DNP3",
    "iec104": "IEC-104",
    "s7": "S7",
    "iec61850": "IEC 61850",
    "other": "Annet",
}

DIFFICULTIES = {"easy": "Lett", "medium": "Middels", "hard": "Vanskelig"}

STATUSES = {
    "solved_alone": "Løst alene",
    "solved_hint": "Løst med hint",
    "solved_solution": "Løst med fasit",
    "unsolved": "Ikke løst",
}

# «Løst» i statistikken = løst alene eller med hint. Fasit teller IKKE som løst,
# slik at svake områder ikke skjules av at du har sett svaret.
SOLVED_STATUSES = {"solved_alone", "solved_hint"}

SECTIONS = [
    "Hva spurte oppgaven om",
    "Min fremgangsmåte",
    "Kommandoer/filtre jeg brukte",
    "Hva som tok tid eller gikk galt",
    "Hva jeg lærte",
]

BODY_TEMPLATE = (
    "## Hva spurte oppgaven om\n\n\n"
    "## Min fremgangsmåte\n\n\n"
    "## Kommandoer/filtre jeg brukte\n\n```\n\n```\n\n"
    "## Hva som tok tid eller gikk galt\n\n\n"
    "## Hva jeg lærte\n\n"
)

# Minste antall oppgaver i en gruppe før den kan havne på «svakeste områder».
MIN_SAMPLES_WEAK = 2
