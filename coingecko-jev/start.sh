#!/bin/zsh
# Launch the CoinGecko × Jev demos on http://127.0.0.1:8787 (keys stay server-side, never sent to the browser).
set -euo pipefail
cd "$(dirname "$0")"

for f in ~/.coingecko/keys.env ~/.typesafe/keys.env; do
  if [[ ! -f "$f" ]]; then
    echo "Missing $f — see the 'Get your keys' section in README.md. A CoinGecko API key is always required (a free Demo key is enough for some demos)." >&2
    exit 1
  fi
done

# Sourcing keys.env can carry its own CG_API_MODE default — let an explicit
# `CG_API_MODE=demo ./start.sh` override it rather than being silently clobbered.
_cg_mode="${CG_API_MODE:-}"
set -a
source ~/.coingecko/keys.env
source ~/.typesafe/keys.env
set +a
[[ -n "$_cg_mode" ]] && export CG_API_MODE="$_cg_mode"

if [[ "${CG_API_MODE:-pro}" == "demo" ]]; then
  if [[ -z "${COINGECKO_DEMO_API_KEY:-}" ]]; then
    echo "COINGECKO_DEMO_API_KEY is empty — check ~/.coingecko/keys.env (CG_API_MODE=demo needs it)." >&2
    exit 1
  fi
elif [[ -z "${COINGECKO_PRO_API_KEY:-}" ]]; then
  echo "COINGECKO_PRO_API_KEY is empty — check ~/.coingecko/keys.env." >&2
  exit 1
fi
if [[ -z "${TYPESAFE_API_KEY:-}" ]]; then
  echo "TYPESAFE_API_KEY is empty — check ~/.typesafe/keys.env." >&2
  exit 1
fi

PORT="${JEV_DEMO_PORT:-8787}"
if [[ "${1:-}" != "--no-open" ]]; then
  (sleep 2 && open "http://127.0.0.1:${PORT}/") &
fi
exec .venv/bin/uvicorn app.server:app --host 127.0.0.1 --port "$PORT" --log-level warning
