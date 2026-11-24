#!/usr/bin/env bash
# Start CTF-tracker: stops an old copy of this app on the same port, opens your browser and runs the server.
#   ./run.sh          Stop with Ctrl+C (not Ctrl+Z).
# Settings come from config.json (see config.example.json) or from the environment (CTF_DATA_DIR, CTF_DOWNLOADS_DIR, CTF_PORT).
set -u
cd "$(dirname "$(readlink -f "$0")")"

[ -x .venv/bin/python ] || { echo "Run ./setup.sh first."; exit 1; }
PORT="${CTF_PORT:-5000}"
export CTF_PORT="$PORT"
URL="http://127.0.0.1:${PORT}"

# 1) Is the port held by an old copy of THIS app (also one paused with Ctrl+Z)? Stop it. Never touch other programs.
pid="$(ss -ltnp 2>/dev/null | sed -n "s/.*:${PORT} .*pid=\([0-9]*\).*/\1/p" | head -1)"
if [ -n "$pid" ]; then
  if tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q -- '-m app'; then
    echo "Stopping the old copy of the app (pid $pid) ..."
    kill -9 "$pid" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do ss -ltn 2>/dev/null | grep -q ":${PORT} " || break; sleep 0.5; done
  else
    echo "ERROR: port ${PORT} is used by another program (pid $pid), not by CTF-tracker. Leaving it alone."
    echo "Use another port:  CTF_PORT=5001 ./run.sh"
    exit 1
  fi
fi

# 2) Is the data folder reachable? (External drives can drop out.)
DATA="$(.venv/bin/python -c 'from app import config; print(config.get_data_dir() or "")' 2>/dev/null)"
if [ -z "$DATA" ]; then
  echo "WARNING: no data folder configured. Run ./setup.sh or set data_dir in config.json."
elif [ ! -d "$DATA" ]; then
  echo "WARNING: $DATA not found. Is the drive connected? The app will start but cannot save."
fi

# 3) Open the browser once the server answers.
if [ -z "${CTF_NO_BROWSER:-}" ]; then
  (
    for _ in $(seq 1 30); do
      if curl -fs -o /dev/null "$URL/"; then
        if command -v wslview >/dev/null 2>&1; then wslview "$URL" >/dev/null 2>&1
        elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
        elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1
        elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$URL" >/dev/null 2>&1
        fi
        exit 0
      fi
      sleep 0.5
    done
  ) &
fi

echo "CTF-tracker is running at $URL  (Ctrl+C to stop)"
exec .venv/bin/python -m app
