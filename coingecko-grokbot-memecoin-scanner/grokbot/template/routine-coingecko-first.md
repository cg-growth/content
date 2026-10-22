# Routine: CoinGecko-first scanner
Schedule: every 15 minutes by default (30–60 min uses less Grok Bot quota). **Paper trading only.**

**If setup hasn't been completed, stop quietly.** Install dir: `D="${MEMESCAN_HOME:-$HOME/coingecko-grokbot-memecoin-scanner}"`. Setup is complete when `$D/start.sh` exists and `COINGECKO_DEMO_API_KEY` or `COINGECKO_PRO_API_KEY` is set. Never print a key.

The services already poll new pools on every enabled chain, run quick filters and deep research, and queue candidates in `pending_research.json`. Your job is the judgment scripts can't do: wallet look-ups when the plan includes them, X buzz, narrative and verdict.

Work in `$D`. Use `.venv/bin/python` for every script.

1. **Health:** `./status.sh`. If the supervisor is down, run `./start.sh`. If it reports a missing key, stop and tell the owner once.
   If `notices/pending.json` has plan or quota notes, post each `text` as its own message in this chat, then `.venv/bin/python lib/plan_tips.py ack <id>`.
2. **Rules:** read `docs/SCOUT.md` and `docs/PLANS.md`.
3. **Queue:** read `pending_research.json`. Take items whose `source` isn't `x-first`, oldest first, max ~6. For each, open `payload_file`:
   - **Wallets:** only if `./status.sh` shows wallet checks are on this plan (a CoinGecko API Analyst plan or higher). If the payload says they are not available, skip the lookup. A skipped check is not a fail and is not a reason to discard. When the checks are on and wallets are unverified, look up new top traders with CoinGecko wallet PnL and wallet trades (Solana addresses are case-sensitive; see `docs/MULTICHAIN.md`), save with `.venv/bin/python walletdb.py upsert`, then `.venv/bin/python walletdb.py score-token --save`.
   - **X buzz (CA-first):** search X for the exact contract address first, then the ticker. Count distinct non-shill authors. Drop namesakes. Copy-paste calls, "DM for VIP" shillers, call bots and paid groups are not organic.
   - **Verdict:** `Organic Hype` (healthy human mix, real multi-author buzz on the exact CA, sane holders), `Watch` (promising but thinner), `Scout` (near-miss per `docs/SCOUT.md`), or `discard`.
   - **Never alert on:** honeypot, rug or liquidity collapse, top10 > 60%, dev > 20%, bot- or bundle-dominated, dust or wash volume, NSFW (`is_nsfw` / `reason_line`), a deployer or large liquidity removal (`reason_line`), or impersonation tokens (`auto/impersonation.json`) unless the exact CA has organic buzz. If `reason_line` is set, the verdict is Discard: record `rule` as that line and do not send a card.
   - **Card:** for Organic Hype, Watch or Scout, write a 2–4 sentence narrative citing the X posts, build `alert.json` (`docs/REALTIME.md`), run `.venv/bin/python alerts/send_card.py alert.json`. If it prints `scout refused` or `muted`, don't retry.
   - **Record:** `echo '<json>' | .venv/bin/python scripts/assess.py record <network> <ca>` (include `x_ca_authors`), then `.venv/bin/python lib/fwdq.py done <ca>`.
4. **Summary:** pipe one line per token plus `N Organic Hype / N Watch / N Scout / N Discard` to `.venv/bin/python scripts/assess.py log`. Stay silent on Telegram if nothing qualifies.

**Budget:** ~2–3 X searches per candidate, at most ~12 per run. If fewer than 150 X reads remain today, check exact CAs only.

**Hard rules:** paper only. Never execute a trade from this routine. Never wire live trading, wallets, private keys or exchange keys unless the owner builds that and asks. Never print secrets. Verdicts are research, not financial advice.
