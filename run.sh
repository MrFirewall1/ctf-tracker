#!/usr/bin/env bash
# Starter CTF-tracker med ett kommando: stopper en gammel kopi av appen, setter innstillingene og åpner nettleseren.
#   ./run.sh            (eller bare:  ctf)
# Stopp med Ctrl+C (ikke Ctrl+Z).
set -u
cd "$(dirname "$(readlink -f "$0")")"

export CTF_DATA_DIR="${CTF_DATA_DIR:-/mnt/d/ctf-data}"
export CTF_DOWNLOADS_DIR="${CTF_DOWNLOADS_DIR:-/mnt/d/ctf-downloads/ICS-PCAP-data}"
PORT="${CTF_PORT:-5000}"
export CTF_PORT="$PORT"
URL="http://127.0.0.1:${PORT}"

# 1) Er porten opptatt av en gammel kopi av DENNE appen (også en som er satt på pause med Ctrl+Z)? Stopp den.
pid="$(ss -ltnp 2>/dev/null | sed -n "s/.*:${PORT} .*pid=\([0-9]*\).*/\1/p" | head -1)"
if [ -n "$pid" ]; then
  if tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q -- '-m app'; then
    echo "Stopper gammel kopi av appen (pid $pid) ..."
    kill -9 "$pid" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do ss -ltn 2>/dev/null | grep -q ":${PORT} " || break; sleep 0.5; done
  else
    echo "FEIL: port ${PORT} brukes av et annet program (pid $pid), ikke av CTF-tracker. Jeg lar det være."
    exit 1
  fi
fi

# 2) Er SSD-en med? Appen starter uansett, men kan ikke lagre uten.
if [ ! -d "$CTF_DATA_DIR" ]; then
  echo "ADVARSEL: finner ikke $CTF_DATA_DIR. Er SSD-en koblet til? (Hvis D: har falt ut: 'wsl --shutdown' i PowerShell.)"
fi

# 3) Åpne nettleseren (Windows) når serveren svarer.
if [ -z "${CTF_NO_BROWSER:-}" ]; then
  (
    for _ in $(seq 1 30); do
      if curl -fs -o /dev/null "$URL/"; then
        if command -v wslview >/dev/null 2>&1; then wslview "$URL" >/dev/null 2>&1
        elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$URL" >/dev/null 2>&1
        fi
        exit 0
      fi
      sleep 0.5
    done
  ) &
fi

echo "CTF-tracker kjører på $URL  (Ctrl+C for å stoppe)"
exec .venv/bin/python -m app
