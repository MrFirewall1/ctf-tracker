"""Engangsimport: legger oppgaver fra ICS-PCAP-Challenges (MIT, kun forfatterteksten) inn i app/practice.json.

Bruk (kjør med -I fra et annet sted enn nedlastingsmappen):
    python -I tools/import_ics_pcap.py ~/ctf-downloads/ICS-PCAP-Challenges [antall-vanskelige]

Importerer: alle Easy + alle Medium + et utvalg Hard (standard 12, fra små datasett).
Tar KUN med tittel, scenario, mål og hint. Løsninger og steg-for-steg-kommandoer importeres ikke.
Kjøres på nytt uten duplikater: gamle ics-ot-*-oppføringer byttes ut.
"""
import json
import sys
from pathlib import Path

PREFIX = "ics-"
PROTOCOL_TAGS = [  # første treff vinner
    ("iec104", ["IEC-104", "IEC 60870"]),
    ("dnp3", ["DNP3"]),
    ("s7", ["S7comm", "S7comm-plus", "S7"]),
    ("iec61850", ["IEC 61850", "GOOSE", "MMS", "IEC 61850 GOOSE", "IEC 61850 SV", "IEC 61850 MMS", "R-GOOSE"]),
    ("modbus", ["Modbus/TCP", "Modbus"]),
]
SMALL = 1.0e9  # Hard-utvalget hentes fra datasett under 1 GB


def protocol_of(tags):
    for proto, names in PROTOCOL_TAGS:
        if any(t in names for t in tags):
            return proto
    return "other"


def to_entry(c):
    objectives = " ".join(f"({i}) {o}" for i, o in enumerate(c.get("objectives") or [], 1))
    objective = c.get("scenario", "").strip()
    if objectives:
        objective += f"\n\nMål: {objectives}"
    ds = (c.get("datasets") or [c.get("dataset")])[0]
    return {
        "id": PREFIX + c["id"],
        "kind": "ics-pcap",
        "title": c["title"],
        "source": "ICS-PCAP-Challenges · " + c.get("category", ""),
        "url": "",
        "category": "pcap_ics",
        "protocol": protocol_of(c.get("tags") or []),
        "difficulty": c["difficulty"].lower(),
        "objective": objective,
        "hints": list(c.get("hints") or []),
        "tags": ["pcap", "ics"] + [t.lower().replace(" ", "-") for t in (c.get("tags") or [])[:3]],
        "data": ds,
        "files": list(c.get("files") or [])[:4],
    }


def main(argv):
    repo = Path(argv[0]).expanduser()
    n_hard = int(argv[1]) if len(argv) > 1 else 12
    cat = json.loads((repo / "catalog" / "challenges.json").read_text(encoding="utf-8"))
    sizes = {}
    for d in json.loads((repo / "catalog" / "datasets.json").read_text(encoding="utf-8")):
        for k in ("id", "slug"):
            if d.get(k):
                sizes[d[k]] = d.get("approx_bytes") or 0

    easy = [c for c in cat if c["difficulty"] == "Easy"]
    medium = [c for c in cat if c["difficulty"] == "Medium"]
    hard = [c for c in cat if c["difficulty"] == "Hard"
            and all(sizes.get(s, 1e12) < SMALL for s in (c.get("datasets") or []))]
    # Variasjon: ta ett fra hver (protokoll) om gangen
    by_proto = {}
    for c in sorted(hard, key=lambda c: c["id"]):
        by_proto.setdefault(protocol_of(c.get("tags") or []), []).append(c)
    picked = []
    while len(picked) < n_hard and any(by_proto.values()):
        for p in list(by_proto):
            if by_proto[p] and len(picked) < n_hard:
                picked.append(by_proto[p].pop(0))

    order = {"easy": 0, "medium": 1, "hard": 2}
    new = sorted((to_entry(c) for c in easy + medium + picked),
                 key=lambda e: (order[e["difficulty"]], e["title"].lower()))

    pj = Path(__file__).resolve().parent.parent / "app" / "practice.json"
    old = json.loads(pj.read_text(encoding="utf-8"))
    kept = [e for e in old if not e["id"].startswith(PREFIX + "ot-")]
    pj.write_text(json.dumps(kept + new, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Beholdt {len(kept)}, importerte {len(new)} "
          f"(easy {len(easy)}, medium {len(medium)}, hard {len(picked)}) -> {pj}")


if __name__ == "__main__":
    main(sys.argv[1:])
