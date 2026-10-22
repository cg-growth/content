# Scout tier (near-miss) — REQUIRED reading for every routine run

## CoinGecko-first scanner routine
When a `[research] SCOUT (near-miss)` forward arrives, or your own read finds a discard whose reasons are only soft (human 50–60, wallets unverified, small bundles <=15% of supply, thin/single-author buzz) with strong momentum (score >=55, h1 >=+15%, >=40 buyers/h, buy-flow >=55%, live liquidity >=$10k, pool >=10 min old). On a CoinGecko API Demo (free) key and on the CoinGecko API Basic plan, top-trader and wallet checks are not included: a missing wallet label is not a fail and is not by itself a Scout reason. "Wallets unverified" applies when those lookups ran and the labels are still unknown:
1. Search X for the EXACT CA (not just ticker). Count distinct non-shill authors. If 0, or live namesakes exist and the CA has no buzz -> discard (copycat).
2. Never Scout on: honeypot, rug/liquidity collapse, human <30, bot/bundle dominated, insider heavy, top10 >60%, dev >20%, dust/wash, stock/brand/celebrity impersonation (MSFT, META, TESLA, SpaceX, NASDAQ variants, Coca-Cola, MrBeast, tokenized-stock wording) unless exact CA has buzz.
3. Otherwise write a short narrative and send with `alerts/send_card.py` using "tag":"Scout", "confidence":"low", "caveats":[each reason it missed], "ca_buzz_authors":<count>, plus usual narrative/x_links/metrics. Script enforces 3/h, one per CA, liq >=$10k, 0.4x sizing; if it prints "scout refused", don't retry.
4. Record state.json assessed[<net>_<ca>] with "verdict":"Scout" and "x_ca_authors":<count>. Also add x_ca_authors for Watch and Organic Hype verdicts (the AI book needs exact-CA buzz to enter).
5. Summary line: "N Organic Hype / N Watch / N Scout / N Discard".

## X-first scanner routine
Queue items with prelim_verdict "Scout?" carry scout_caveats. Apply the same rule: confirm exact CA from >=1 non-shill author, reject copycats/impersonators without exact-CA buzz and any hard reason. Send with "tag":"Scout", "caveats": scout_caveats + findings, "ca_buzz_authors":<count>, "source":"x-first". state.json verdict "Scout" with x_ca_authors. Summary line includes Scout count.

## Telegram free-form handler
Scout cards (🔭 SCOUT · near-miss) are lower conviction. "Why is this a scout" -> answer from the card's "Why it missed" caveats and the research file. Text buys of a Scout without amount -> use the card's Scout size, not Watch size. "How are scouts doing"/"scout hit rate" -> run `.venv/bin/python tracker/tracker.py --stats` and report hit rate (>=1.5x) and avg 1h/24h return per tier.
