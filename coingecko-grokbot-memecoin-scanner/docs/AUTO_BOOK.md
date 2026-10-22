# AI Autonomous Paper Book (book id `auto`)
PAPER only. Ledger `auto.db` (WAL, own file; same schema as paper.db + `trades.rationale`, `trades.tier`, `notices`, `auto_seen`). Both books use `PAPER_START_CASH` (default $10,000). A book with no trades adopts it on startup, which also sets `start_cash` in `policy.json`. A book that already has trades is left as it is.
Human book (`paper.db`) is never written by these processes.

Processes (supervise.sh): `auto/autotrader.py` (entries, notices digest, tuner every 6h) and `auto/risk_auto.py`
(= risk/risk.py with BOOK=auto, PAPER_DB=auto.db: notify→notices table, ask()→executes immediately, time-stop auto-sells,
position_meta.auto_clip=1, policy.json `risk_overrides` merged over risk.json).

Entry: candidates = market.db `deep:*` discoveries (≤15 min) + state.json AI verdicts + xfirst queue. CA-first always.
Tiers: organic (AI verdict Organic Hype, mult 1.0) · watch (verdict Watch*, score≥65, human≥45; ships disabled at mult 0.1 because it lost money in testing; re-enable in policy.json) ·
scout (soft discard only, h1≥+15%, buyers/h≥40, flow≥0.55, human≥40 or unverified, score≥50, liq≥$8k, m5≥0; mult 0.3).
Hard blocks: honeypot, top10>60% ex-pools, dev>20%, liq<$5k, human<30, bot/bundle dominated / insider heavy, bundle in top10,
rug words, and LIVE liquidity < max($5k, 50% of research liq) at entry time (pool-pulled guard).
Sizing: min(2.5% equity × tier mult, sizing.recommend (pool-median) × tier mult, 5% equity, 1% of live liq, $600, 90% cash); ≥$15.
Honeypot unknown → ×0.5. Token buy/sell taxes (if CG/GT expose them) applied as qty haircut. Caps: 8 open, 50% exposure, 4/chain, 120 min per-ticker cooldown.
Fills: core.buy / clips.fill (constant-product slippage, DEX fee, per-chain gas).
Exits: risk engine — SL −40% (8 min grace), trail 22% after +40%, ladder initial@2x, orig20@3.5x, orig15@6x (auto-clip ON), danger + rug exits, time-stop 3h if < +5%.
Tuner (`auto/tuner.py`): per tier, n≥5 closed sells: PnL>0 & win≥40% → mult×1.10 (≤1.5); PnL<0 → ×0.85 (≥0.10; disable at floor with n≥10).
Time-stop hours ±0.5 (1.5–6h) by avg time-stop PnL. Changes logged to auto/policy_history.jsonl.
Telegram (read-only): /auto, /autoreport, /compare, keyboard "🤖 AI Book" / "⚖️ Compare", NL "how is your book doing", "compare books".
Notices: risk.json `auto_book.notify` (default true), ≤1 message / 60 s, digest when several.
Dashboard: tab "🤖 AI Book" (compare + positions + ledger + policy), /api/auto, /api/compare.

## Tick sanitation — lib/ticks.py, used by both books
quote(): price from the deepest pool itself (not token-level price_usd) → ticks.sane(). cached_quote() (G1) → sane(). risk.price() → sane()
(SL/trail/clip/TP). pool_reserve(): same pool only. Buys: CP impact U/(liq/2). Clips refused if position value > 5× pool; ≤20 tranches.
Thresholds (risk.json "tick_sanity" overrides): dust $1, window 300s/40 prints (fallback OHLCV 15m, then 6h history), log-MAD band
max(35%, 6·MAD) capped 3×, big move needs ≥2 distinct non-dust trades within 15% in 45s, units check usd/pu vs amount ±50%.
Rejects → ticks.db (rejects, counts) + "[ticks] REJECT" log lines. Added after an audit found a few absurd AI-book wins were artifacts of bad prints (wrong pool, dust trades, unit mismatches), not real fills.

## Entry filters (lib/entryfilters.py, policy.json `entry_filters`)
- Impersonation block: names/tickers fuzzy-matching `auto/impersonation.json` (stocks, big brands, celebrities, tokenized-stock words) are never bought unless the exact CA has organic X buzz.
- Watch/Scout entries need ≥1 non-shill X author posting the exact CA.
- No pools younger than 10 min or with live liquidity < $10k.
- Size weighted toward the "winner profile" (sustained non-dust volume, steady multi-minute climb).
