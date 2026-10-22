# X-first discovery (reverse workflow)

CG-first: CoinGecko new pools → wallet checks → X buzz → card.
X-first: **X buzz → CA → CoinGecko pool → same gates → wallet checks → card.**

Only the agent can call the X MCP, so the agent runs the searches and `xfirst/xfirst.py` does everything else on the box.

## Budget
Typical X MCP limits are about 30 reads/min and 1000/day (check yours), shared with the CG-first checks. Each search returns at most 25 posts.
- X-first uses **2 calls per 15-min cycle** (≈192/day). Q3 is optional: use it only when the minute and day budgets allow.
- CG-first CA checks keep using about 2–3 calls per cycle.
- Each tool result prints how many reads are left. If fewer than 150 are left for the day, run only Q1.

## Per-cycle searches (search_posts_all)
Always pass these args:
`max_results:25, sort_order:"recency", start_time:<now-20min, UTC Z>, post.fields:"created_at,public_metrics,author_id,entities", expansions:"author_id", user.fields:"username,public_metrics,created_at,verified"`
Set `write_to_file:true` and copy the result file into `xfirst/inbox/`.

**Q1, EVM chains (the main chains):**
```
("robinhood chain" OR #base OR "on base" OR bsc OR four.meme OR clanker OR zora OR bnb) (CA OR 0x) -giveaway -airdrop -"DM for" -VIP -presale -is:retweet -is:reply
```
**Q2, any chain CA drops (catches Solana runners):**
```
(CA OR "contract" OR pump) (base OR bsc OR solana OR robinhood) (memecoin OR "low cap" OR gem OR ape) -giveaway -airdrop -"DM for" -VIP -is:retweet -is:reply lang:en
```
**Q3 (optional, every other cycle). Engagement-weighted, uses `sort_order:"relevancy"`, start_time now-2h:**
```
(CA OR 0x OR pump.fun) (memecoin OR "just launched" OR stealth) -giveaway -airdrop -"DM for" -VIP -"private TG" -is:retweet -is:reply
```
The X API has no min_faves operator here, so engagement is scored in the script: likes + 2×RT + replies + 2×quotes, plus author followers and account age.

## Command sequence (each cycle, after the CG-first backstop)
1. Run Q1 and Q2 (and Q3 if allowed) with write_to_file. Then `cp <result file> xfirst/inbox/q1_$(date +%H%M).txt` (paths are relative to this folder; do the same for q2).
2. `cd <this folder> && .venv/bin/python xfirst/xfirst.py run --top 3`
   - Takes about 5–30s and uses about 1 CG credit per CA plus about 5 per deep check.
   - Prints a summary line and one row per CA: stage, network, symbol, buzz score/grade, unique authors and reason.
   - Writes `xfirst/last_run.json` and `xfirst/runs/<ts>/candidates.json`, and moves the inbox files into the run folder.
3. `.venv/bin/python xfirst/xfirst.py queue`. Any items are also listed in `pending_research.json` with `"source":"x-first"`.
4. For each queued item, open `payload_file` (research JSON with `buzz`, `x_posts` and `x_links`). Then:
   - If wallets are unverified, PnL-profile the top traders as in trader-research.md and run `walletdb.py upsert` / `score-token --save`.
   - Decide **Organic Hype / Watch / Discard** using the same rules as CG-first. The buzz must be real: a single VIP/"DM for access" shiller, copy-paste text or a ticker that is already 10x is *not* organic.
   - Only for Organic Hype or Watch: write the narrative citing the X posts, then build alert.json with `"source":"x-first"` and `x_links` from the payload, and run `.venv/bin/python alerts/send_card.py alert.json`.
   - Run `.venv/bin/python xfirst/xfirst.py done <ca>` (the same as `lib/fwdq.py done <ca>`).
5. Record every deep-checked token in `state.json.assessed` with `"source":"x-first"` so the dashboard shows the badge and it isn't re-assessed.
6. In log.md, add this line under the run header (the dashboard parses `X-first: N`):
   `X-first: N candidates (posts P, CAs C; G gate-pass, D deep, Q queued) · X calls K`
   Keep the usual `N Organic Hype / N Watch / N Discard` line covering both sources.

## Rules the script applies
- **Extract:** EVM `0x…40hex` and Solana base58 (32–44 chars, mixed case + digit, outside URLs, not part of an 0x address), plus cashtags.
- **Dedupe:** skips anything already in state.json (assessed/pending), the discoveries table or the x-first queue. A previously discarded token is rechecked only if buyers_h1 or liquidity grew 50% or more.
- **Resolve:** `/onchain/search/pools?query=<CA>`, keeping only pools on solana/robinhood/base/bsc whose base token is the CA. Picks the deepest pool.
- **Gates:** discovery's `quick()` with the `risk.json["xfirst"]` overrides (age ≤72h, liq ≥$5k, FDV $8k–$5M, buyers_h1 ≥15, h1 −60%…+5000%, no-sells honeypot check).
- **Buzz pass:** grade not shill/thin, OR 3+ unique authors, OR market-confirmed (buyers_h1 ≥300 and liq ≥$20k).
- **Deep check:** `discovery._deep` (holders, top traders, trade tape, wallets.db score-token, smart-money lookup) in DRY mode, so nothing is forwarded to the webhook. The script adds `source`, `buzz`, `x_posts` and `x_links` to the research JSON.
- **Queue:** a token is queued if its prelim verdict is not discard, or if its buzz grade is organic.


## Multi-chain
See `docs/MULTICHAIN.md`. Solana CAs keep base58 casing end-to-end; ticker buys never silently pick an EVM namesake — Telegram shows pick buttons.

## Scout tier (near-miss)
After deep research, a `discard` whose fail reasons are ALL soft (human below 60 but >= 50, unverified wallets, bundled wallets
holding <= 15% of supply in the top 10, single-author/thin buzz) AND has strong momentum (score >= 55, h1 >= +15%, buyers/h >= 40,
buy-flow >= 0.55, m5 >= 0, live liquidity >= $8k re-checked at queue time) becomes `prelim_verdict: "Scout?"` with `scout_caveats`.
Never Scout: honeypot, rug/liquidity collapse, bot farm (human < 30), bot/bundle dominated, insider heavy, top10 > 60%, dev > 20%,
dust/wash (avg trade < $3), namesake/copycat with 0 CA buzz, tokens older than 12h, CAs already alerted.
Caps: 6 Scout forwards/h, 3 Scout cards/h, one per CA ever (scout.db). Card: tag "Scout", `caveats` list required, size 0.4x Watch.
Thresholds: risk.json "scout". Logic: lib/scout.py (shared with discovery). Outcomes: tracker `--stats` (hit = max >= 1.5x).
