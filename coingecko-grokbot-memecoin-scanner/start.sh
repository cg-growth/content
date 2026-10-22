#!/usr/bin/env bash
# Start the paper-trading memecoin scanner: creates local DBs if missing, then launches the supervisor
# (stream, discovery, risk, tracker, AI book, Telegram bot, dashboard on http://127.0.0.1:${PORT:-8787}).
# Keys are read from files OUTSIDE the repo (or from the environment, e.g. Grok Bot secrets) and are never printed.
#   ./start.sh            start (idempotent)
#   ./start.sh --init-only  just create the databases
set -euo pipefail
cd "$(dirname "$0")"
export MEMESCAN_HOME="$(pwd)"
PY=".venv/bin/python"; [ -x "$PY" ] || { echo "No .venv yet - run ./install.sh first." >&2; exit 1; }

# 1) Keys: environment wins. Keys files only fill names that are empty. Files are not executed.
# Loaded before the databases so PAPER_START_CASH is the bankroll a fresh book adopts.
# shellcheck source=scripts/load_keys.sh
source "$MEMESCAN_HOME/scripts/load_keys.sh"
memescan_load_keys

# 2) Local databases (no CoinGecko key needed). A book with no trades adopts PAPER_START_CASH.
"$PY" scripts/init_db.py >/dev/null || { echo "Database init failed - see the message above." >&2; exit 1; }
[ "${1:-}" = "--init-only" ] && { echo "Databases ready."; exit 0; }

if [ -z "${COINGECKO_PRO_API_KEY:-}" ] && [ -z "${COINGECKO_DEMO_API_KEY:-}" ]; then
  echo "This scanner needs a CoinGecko API key. A CoinGecko API Demo (free) key is enough to start: it gives the scanner its own rate limit (100 calls/min and 10,000 calls/month on the CoinGecko API Demo (free) plan) instead of the shared keyless limit." >&2
  dash="$("$PY" -c 'import sys; sys.path.insert(0,"lib"); import utm; print(utm.developer_dashboard("start-no-key"))')"
  price="$("$PY" -c 'import sys; sys.path.insert(0,"lib"); import utm; print(utm.pricing("start-no-key-pricing"))')"
  echo "New to CoinGecko API? Sign up for a CoinGecko API Demo (free) plan or a paid plan on the CoinGecko API pricing page. Sign-up opens the developer dashboard, where you copy the key: $price" >&2
  echo "Already have a CoinGecko API account? Copy the key from the developer dashboard: $dash" >&2
  exit 1
fi
# One bankroll for both books. A book with no trades adopts PAPER_START_CASH here, including a book install.sh created earlier at the default.
"$PY" -c '
import os, sys
sys.path[:0] = ["lib", "telegram"]
import core
root = os.environ.get("MEMESCAN_HOME") or os.getcwd()
for name in ("paper.db", "auto.db"):
    path = os.path.join(root, name)
    if os.path.exists(path):
        core.apply_book(path)
'
tier_out="$("$PY" "$MEMESCAN_HOME/lib/cgtier.py" --export)" || exit 1
while IFS= read -r line; do
  case "$line" in
    export\ CG_*=*) eval "$line" ;;
  esac
done <<< "$tier_out"
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "Note: TELEGRAM_BOT_TOKEN not set - running without Telegram alerts/buttons (dashboard + paper books still run)." >&2
fi
if [ "${CG_TIER:-}" = "demo" ]; then
  "$PY" "$MEMESCAN_HOME/lib/credits.py" >&2 || true
fi
for v in COINGECKO_PRO_API_KEY COINGECKO_DEMO_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID TELEGRAM_FORWARD_URL TELEGRAM_FORWARD_KEY MEMESCAN_TZ PAPER_START_CASH PORT CHROME_BIN CG_TIER CG_BASE CG_AUTH_HEADER CG_KEY_ENV CG_PLAN; do
  [ -n "${!v:-}" ] && export "$v"
done

# 3) Supervisor (single instance)
if pgrep -f memescan-supervise >/dev/null 2>&1; then echo "Already running. ./status.sh to check, ./stop.sh to stop."; exit 0; fi
if command -v setsid >/dev/null 2>&1; then
  setsid nohup bash -c "exec -a memescan-supervise bash '$MEMESCAN_HOME/scripts/supervise.sh'" >/dev/null 2>&1 < /dev/null &
else
  nohup bash -c "exec -a memescan-supervise bash '$MEMESCAN_HOME/scripts/supervise.sh'" >/dev/null 2>&1 < /dev/null &
fi
sleep 2
pgrep -f memescan-supervise >/dev/null 2>&1 || { echo "Supervisor failed to start - check logs/supervise.log" >&2; exit 1; }
echo "Started (paper trading only). Dashboard: http://127.0.0.1:${PORT:-8787}  ·  status: ./status.sh  ·  logs: logs/"
[ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -z "${TELEGRAM_CHAT_ID:-}" ] && [ ! -f telegram/owner.json ] && echo "Telegram: send /start to your bot from your own account to register as owner."
exit 0
