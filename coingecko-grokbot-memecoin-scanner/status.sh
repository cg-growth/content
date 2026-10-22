#!/usr/bin/env bash
# Read-only status of each service.
cd "$(dirname "$0")"; B="$(pwd)"; PORT="${PORT:-8787}"
pgrep -f memescan-supervise >/dev/null && echo "supervisor  up" || echo "supervisor  DOWN"
for n in stream:stream/stream.py risk:risk/risk.py discovery:discovery/discovery.py tracker:tracker/tracker.py \
         autotrader:auto/autotrader.py risk_auto:auto/risk_auto.py telegram:telegram/daemon.py; do
  printf "%-11s " "${n%%:*}"; pgrep -f -- "-u $B/${n#*:}" >/dev/null && echo up || echo DOWN
done
printf "%-11s " dashboard; curl -s -o /dev/null -m 5 "http://127.0.0.1:$PORT/" && echo "up (http://127.0.0.1:$PORT)" || echo DOWN
PY=".venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"
"$PY" -c "import sys; sys.path.insert(0,'lib'); import plan_tips; print(plan_tips.status_text())" 2>/dev/null || true
[ -f logs/supervise.log ] && tail -n 1 logs/supervise.log
