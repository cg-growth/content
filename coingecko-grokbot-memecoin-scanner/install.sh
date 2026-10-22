#!/usr/bin/env bash
# One-time setup: Python virtualenv + dependencies + empty local databases. Linux + macOS. No keys needed.
set -euo pipefail
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r requirements.txt
  [ "${WITH_VOICE:-0}" = 1 ] && uv pip install --python .venv/bin/python -r requirements-voice.txt
else
  PY="$(command -v python3 || true)"
  [ -n "$PY" ] || { echo "python3 not found. Install Python 3.10+ (or uv: https://docs.astral.sh/uv/)." >&2; exit 1; }
  "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { echo "Python 3.10+ required (found $("$PY" -V))." >&2; exit 1; }
  "$PY" -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
  .venv/bin/python -m pip install -q -r requirements.txt
  [ "${WITH_VOICE:-0}" = 1 ] && .venv/bin/python -m pip install -q -r requirements-voice.txt
fi
.venv/bin/python scripts/init_db.py
command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1 \
  || [ -d "/Applications/Google Chrome.app" ] || echo "Note: Chrome/Chromium not found - portfolio/report image cards need it (or set CHROME_BIN)."
echo "Installed. Next: put your keys in ~/.coingecko/keys.env (see README 'Get your keys'), then ./start.sh"
