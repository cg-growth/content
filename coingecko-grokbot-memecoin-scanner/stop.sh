#!/usr/bin/env bash
# Stop everything this folder started (supervisor first so nothing restarts). Data is kept.
cd "$(dirname "$0")"; B="$(pwd)"
pkill -f memescan-supervise 2>/dev/null
pkill -f "memescan-.*-loop" 2>/dev/null
for s in stream/stream.py risk/risk.py discovery/discovery.py tracker/tracker.py auto/autotrader.py auto/risk_auto.py telegram/daemon.py dashboard/server.py; do
  pkill -f -- "-u $B/$s" 2>/dev/null
done
sleep 1; echo "Stopped. Databases and logs are kept."
