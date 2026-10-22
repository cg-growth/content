# Routine: X-first scanner
Schedule: every 15 minutes by default. Run it instead of, or as well as, the CoinGecko-first scanner (both use more Grok Bot quota). **Paper trading only.**

**If setup hasn't been completed, stop quietly.** Install dir: `D="${MEMESCAN_HOME:-$HOME/coingecko-grokbot-memecoin-scanner}"`. Setup is complete when `$D/start.sh` exists and `COINGECKO_DEMO_API_KEY` or `COINGECKO_PRO_API_KEY` is set. Never print a key.

Reverse workflow: **X buzz → contract address → CoinGecko pool → same gates → wallet checks when the plan includes them → card.** Only you call X. `xfirst/xfirst.py` does the rest. It resolves pools on `discovery.networks` in `risk.json`, or on `xfirst.networks` when that list is set. Full spec: `docs/XFIRST.md`.

Work in `$D`. Use `.venv/bin/python`.

1. **Health:** `./status.sh`. If the supervisor is down, run `./start.sh`. If it reports a missing key, stop and tell the owner once.
2. **X searches:** run **Q1** and **Q2** from `docs/XFIRST.md`. Q3 only every other run, and only if the daily budget allows. Use `max_results:25`, `sort_order:"recency"`, `start_time` = now − 20 min (UTC, `Z`), and the fields listed there. Save raw results to `xfirst/inbox/q1_<HHMM>.txt` and `xfirst/inbox/q2_<HHMM>.txt`.
3. **Resolve and gate:** `.venv/bin/python xfirst/xfirst.py run --top 3`.
4. **Queue:** `.venv/bin/python xfirst/xfirst.py queue`. For each item, decide as in the CoinGecko-first routine: wallet look-ups only on a CoinGecko API Analyst plan or higher (a skipped check is not a fail), CA-first buzz, the impersonation block, then the verdict. For Organic Hype, Watch or Scout, send the card with `"source":"x-first"` and the payload's `x_links`, then `.venv/bin/python xfirst/xfirst.py done <ca>`.
5. **Record and log:** `scripts/assess.py record` with `"source":"x-first"`. Pipe `X-first: N candidates (posts P, CAs C; G gate-pass, D deep, Q queued) · X calls K` plus the verdict tally to `.venv/bin/python scripts/assess.py log`. Stay silent on Telegram if nothing qualifies.

**Budget:** 2 X calls per run (~192/day at 15 min). If fewer than 150 reads remain today, run only Q1.

**Hard rules:** paper only. Never execute a trade from this routine. Never wire live trading, wallets, private keys or exchange keys unless the owner builds that and asks. Never print secrets. Never alert on impersonation tokens unless the exact CA has organic buzz. Verdicts are research, not financial advice.
