#!/usr/bin/env bash
# One-time setup: virtualenv, dependencies, and a data folder for your own notes.
#   ./setup.sh                       # data goes to ~/ctf-tracker-data
#   CTF_DATA_DIR=/path/to/dir ./setup.sh
set -eu
cd "$(dirname "$(readlink -f "$0")")"

command -v python3 >/dev/null || { echo "python3 is required (3.10 or newer)."; exit 1; }
python3 - <<'PY' || { echo "Python 3.10 or newer is required."; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

DATA="${CTF_DATA_DIR:-$HOME/ctf-tracker-data}"
DATA="${DATA/#\~/$HOME}"
mkdir -p "$DATA"
if [ ! -f config.json ]; then
  printf '{\n  "data_dir": "%s"\n}\n' "$DATA" > config.json
  echo "Wrote config.json (data_dir = $DATA)"
fi
CTF_DATA_DIR="$DATA" .venv/bin/python -m app init

echo
echo "Done. Start the app with:  ./run.sh"
