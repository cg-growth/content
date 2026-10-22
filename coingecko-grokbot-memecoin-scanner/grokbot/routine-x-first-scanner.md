# Routine: X-first scanner
**Trigger:** schedule, every 15 minutes. **Off by default** (turn on instead of, or in addition to, the CoinGecko-first scanner; both = more quota). **Paper only.**

Reverse workflow: **X buzz → contract address → CoinGecko pool → same gates → wallet checks → card.**
Only you can call the X connector; `xfirst/xfirst.py` does everything else on the box. Full spec: `docs/XFIRST.md`.

Work in `<FOLDER>`. Use `.venv/bin/python`. Secrets are in env; never print them.

1. `./status.sh`; if the supervisor is down, run `./start.sh`.
2. Run the X searches **Q1** and **Q2** from `docs/XFIRST.md` (Q3 only every other run and if the daily budget allows) with
   `max_results:25`, `sort_order:"recency"`, `start_time` = now − 20 min (UTC, `Z`), and the post/user fields listed there.
   Save each raw result into `xfirst/inbox/q1_<HHMM>.txt`, `xfirst/inbox/q2_<HHMM>.txt`.
3. `.venv/bin/python xfirst/xfirst.py run --top 3`: extracts EVM + Solana CAs, resolves the deepest CoinGecko pool,
   applies the gates from `risk.json["xfirst"]`, scores buzz, deep-checks the top candidates and queues them.
4. `.venv/bin/python xfirst/xfirst.py queue`. For each item open its `payload_file` and decide exactly as in the
   CoinGecko-first routine (wallet verification, CA-first buzz, impersonation block, verdict). For Organic Hype / Watch / Scout
   send the card with `"source":"x-first"` and the payload's `x_links`; then `.venv/bin/python xfirst/xfirst.py done <ca>`.
5. Record every deep-checked token with `scripts/assess.py record` (`"source":"x-first"`), and log
   `X-first: N candidates (posts P, CAs C; G gate-pass, D deep, Q queued) · X calls K` plus the verdict tally with `scripts/assess.py log`.

Budget: 2 X calls per run (~192/day at 15 min). If fewer than 150 reads remain today, run only Q1.
