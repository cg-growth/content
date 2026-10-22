#!/usr/bin/env bash
# Watchdog for the paper-trading memecoin scanner (bash 3.2+ compatible: Linux + macOS).
# Every 30s: makes sure each service loop is up and its log heartbeat is fresh; restarts stale children;
# pings Telegram if a service stays down > 2 min. Secrets are inherited from the launching shell (start.sh), never written.
# Started by ./start.sh (do not run twice). Status: ./status.sh
cd "$(dirname "$0")/.." || exit 1
B="$(pwd)"; export MEMESCAN_HOME="$B"; L="$B/logs"; mkdir -p "$L"
PY="${MEMESCAN_PYTHON:-$B/.venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
PORT="${PORT:-8787}"; export PORT
SERVICES="stream risk discovery tracker autotrader risk_auto"
script_of(){ case "$1" in
  stream) echo "$B/stream/stream.py";; risk) echo "$B/risk/risk.py";; discovery) echo "$B/discovery/discovery.py";;
  tracker) echo "$B/tracker/tracker.py";; autotrader) echo "$B/auto/autotrader.py";; risk_auto) echo "$B/auto/risk_auto.py";;
  telegram) echo "$B/telegram/daemon.py";; dashboard) echo "$B/dashboard/server.py";; esac; }
mtime(){ stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
fsize(){ stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null || echo 0; }
fresh(){ [ -f "$1" ] && [ $(( $(date +%s) - $(mtime "$1") )) -lt "${2:-180}" ]; }
log(){ echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [supervise] $*" >> "$L/supervise.log"; }
ping_tg(){ [ -n "${TELEGRAM_BOT_TOKEN:-}" ] || return 0
  "$PY" -c "import sys;sys.path.insert(0,'$B/telegram');import core;o=core.owner();o and core.send(o['chat_id'],sys.argv[1])" "$1" >/dev/null 2>&1; }
detach(){ if command -v setsid >/dev/null 2>&1; then setsid nohup "$@" >/dev/null 2>&1 < /dev/null &
          else nohup "$@" >/dev/null 2>&1 < /dev/null & fi; }
start_loop(){ # name script logfile
  detach bash -c "exec -a memescan-$1-loop bash -c 'while true; do \"$PY\" -u \"$2\" >>\"$3\" 2>&1; sleep 3; done'"
  log "started $1"; }
running(){ pgrep -f -- "-u $(script_of "$1")" >/dev/null 2>&1; }   # matches the python child, not its bash loop
loop_up(){ pgrep -f "memescan-$1-loop" >/dev/null 2>&1; }
check(){ # name up(1/0)
  n=$1; now=$(date +%s); dv="DOWN_$n"; pv="PINGED_$n"
  if [ "$2" = 1 ]; then
    [ -n "$(eval echo \${$pv:-})" ] && ping_tg "✅ $n recovered"
    eval "$dv=''; $pv=''"
  else
    [ -z "$(eval echo \${$dv:-})" ] && eval "$dv=$now"
    since=$(eval echo \${$dv}); if [ $((now - since)) -gt 120 ] && [ -z "$(eval echo \${$pv:-})" ]; then
      ping_tg "⚠️ memecoin scanner: $n has been down >2 min (auto-restarting)"; eval "$pv=1"; log "pinged $n"; fi
  fi; }
log "supervisor up (root $B)"
while true; do
  if [ -z "${COINGECKO_PRO_API_KEY:-}" ]; then log "missing COINGECKO_PRO_API_KEY; services not started"; sleep 30; continue; fi
  loop_up dashboard || start_loop dashboard "$(script_of dashboard)" "$L/dashboard.log"
  if curl -s -o /dev/null -m 5 "http://127.0.0.1:$PORT/"; then check dashboard 1; else check dashboard 0; fi
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    loop_up telegram || start_loop telegram "$(script_of telegram)" "$L/telegram.log"
    if running telegram; then check telegram 1; else check telegram 0; fi
  fi
  for n in $SERVICES; do
    lf="$L/$n.log"
    if ! loop_up "$n"; then start_loop "$n" "$(script_of "$n")" "$lf"; check "$n" 0; continue; fi
    if running "$n" && fresh "$lf" 180; then check "$n" 1
    else check "$n" 0; fresh "$lf" 180 || { log "stale heartbeat $n -> restart child"; pkill -f -- "-u $(script_of "$n")"; touch "$lf"; }; fi
  done
  echo "$(date '+%Y-%m-%dT%H:%M:%S%z') [supervise] heartbeat" >> "$L/supervise.log"
  for f in "$L"/*.log; do [ "$(fsize "$f")" -gt 20000000 ] && tail -n 20000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"; done
  sleep 30
done
