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

# 1) Local databases (no keys needed)
"$PY" scripts/init_db.py >/dev/null || { echo "Database init failed - see the message above." >&2; exit 1; }
[ "${1:-}" = "--init-only" ] && { echo "Databases ready."; exit 0; }

# 2) Keys: env vars win; otherwise load the keys files (kept outside this repo)
_cg_mode="${CG_API_MODE:-}"
for f in "$HOME/.coingecko/keys.env" "$HOME/.grokbot-memecoin/keys.env"; do
  if [ -f "$f" ]; then set -a; . "$f"; set +a; fi
done
[ -n "$_cg_mode" ] && export CG_API_MODE="$_cg_mode"
if [ "${CG_API_MODE:-pro}" = "demo" ]; then
  echo "CG_API_MODE=demo is not supported: this scanner needs a paid CoinGecko API plan (Analyst or higher) for onchain top traders/holders, wallet PnL and the WebSocket stream. See README 'Get your keys'." >&2
  exit 1
fi
if [ -z "${COINGECKO_PRO_API_KEY:-}" ]; then
  echo "Missing COINGECKO_PRO_API_KEY - add it to ~/.coingecko/keys.env (or your environment). See README 'Get your keys'." >&2
  exit 1
fi
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "Note: TELEGRAM_BOT_TOKEN not set - running without Telegram alerts/buttons (dashboard + paper books still run)." >&2
fi
export COINGECKO_PRO_API_KEY
for v in TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID TELEGRAM_FORWARD_URL TELEGRAM_FORWARD_KEY MEMESCAN_TZ PAPER_START_CASH PORT CHROME_BIN; do
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
