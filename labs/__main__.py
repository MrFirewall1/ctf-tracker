"""Egne øvelser med tilfeldige flagg. Ingen kjenner svaret på forhånd.

  python -m labs generate <mappe>            lager øvelsene (mappen må være tom/ny)
  python -m labs check <mappe> <lab> <flagg> sjekker svaret ditt
"""
import hashlib
import hmac
import json
import os
import random
import secrets
import sys
from pathlib import Path

from app import config
from .pcap import build_modbus_pcap

LABS = ["hidden-file", "log-secret", "env-leak", "modbus-flag"]
MANIFEST = ".labs.json"


def _flag(prefix: str) -> str:
    return f"CTF{{{prefix}_{secrets.token_hex(4)}}}"


def _digest(salt: str, flag: str) -> str:
    return hashlib.sha256((salt + flag).encode()).hexdigest()


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def generate(target: str) -> dict[str, str]:
    target = Path(target).expanduser().resolve()
    data_dir = config.get_data_dir()
    if data_dir and _inside(target, Path(data_dir).expanduser().resolve()):
        raise SystemExit("Nektet: øvelsesmappen må ligge utenfor datamappen (den blir et git-repo).")
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"Nektet: {target} finnes og er ikke tom. Velg en ny mappe.")
    target.mkdir(parents=True, exist_ok=True)
    rng = random.Random(secrets.randbits(64))
    flags: dict[str, str] = {}

    # 1) skjult fil
    flags["hidden-file"] = f = _flag("hidden")
    root = target / "hidden-file"
    for name in ("notes", "projects", "downloads", "archive"):
        d = root / name
        d.mkdir(parents=True)
        for i in range(rng.randint(2, 4)):
            (d / f"{rng.choice(['report', 'todo', 'draft', 'data'])}_{i}.txt").write_text("ingenting her\n")
    hidden = root / rng.choice(["archive", "projects"]) / ".cache" / f".{secrets.token_hex(3)}"
    hidden.parent.mkdir(parents=True)
    hidden.write_text(f + "\n")

    # 2) hemmelighet i logg
    flags["log-secret"] = f = _flag("logged")
    lvl = ["INFO", "INFO", "INFO", "WARN", "DEBUG"]
    msgs = ["request handled", "cache miss", "user login ok", "connection closed", "retrying upstream",
            "config reloaded", "health check ok", "slow query"]
    lines = [
        f"2026-03-{rng.randint(1, 28):02d} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:"
        f"{rng.randint(0, 59):02d} {rng.choice(lvl)} svc[{rng.randint(100, 999)}]: {rng.choice(msgs)}"
        for _ in range(3000)
    ]
    lines.insert(rng.randint(500, 2500),
                 f"2026-03-14 09:12:44 DEBUG svc[412]: auth fallback used, token={f}")
    (target / "log-secret").mkdir()
    (target / "log-secret" / "server.log").write_text("\n".join(lines) + "\n")

    # 3) miljøvariabel
    flags["env-leak"] = f = _flag("env")
    d = target / "env-leak"
    d.mkdir()
    script = d / "start_service.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        "# Starter en 'tjeneste' i bakgrunnen i én time.\n"
        f"export APP_SECRET='{f}'\n"
        "export APP_MODE=production\n"
        "nohup sleep 3600 >/dev/null 2>&1 &\n"
        "echo \"Tjenesten kjører med PID $!\"\n"
    )
    script.chmod(0o755)

    # 4) Modbus-pcap
    flags["modbus-flag"] = f = _flag("modbus")
    (target / "modbus-flag").mkdir()
    build_modbus_pcap(target / "modbus-flag" / "capture.pcap", f, rng)

    salt = secrets.token_hex(8)
    manifest = {"salt": salt, "labs": {k: _digest(salt, v) for k, v in flags.items()}}
    (target / MANIFEST).write_text(json.dumps(manifest, indent=1))
    return flags


def check(target: str, lab: str, answer: str) -> bool:
    manifest = json.loads((Path(target).expanduser() / MANIFEST).read_text())
    if lab not in manifest["labs"]:
        raise SystemExit(f"Ukjent øvelse. Velg blant: {', '.join(LABS)}")
    return hmac.compare_digest(manifest["labs"][lab], _digest(manifest["salt"], answer.strip()))


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "generate":
        generate(argv[1])  # flaggene skrives bevisst ikke ut
        print(f"Øvelsene ligger i {argv[1]}: {', '.join(LABS)}")
        print("Sjekk svar:  python -m labs check <mappe> <øvelse> '<flagg>'")
        return 0
    if len(argv) == 4 and argv[0] == "check":
        ok = check(argv[1], argv[2], argv[3])
        print("Riktig!" if ok else "Feil, prøv igjen.")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
