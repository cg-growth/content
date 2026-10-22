"""Rebuild ~30d Solana wallet history from CoinGecko PnL + wallet trades (balances/transfers are EVM-only).
Limits (verified 2026-10-14):
  WORKS on solana: /wallets/{addr}/pnl, /networks/solana/wallets/{addr}/trades (cursor), token top_traders,
                   top_holders, holders_chart, info, pool/token trades, ohlcv, simple price.
  FAILS on solana: /wallets/{addr}/balances (400), /networks/solana/wallets/{addr}/transfers (empty/404).
  CASE: Solana addresses are base58 and case-sensitive. Lowercasing returns empty PnL (0 tokens).
  PnL is lifetime (not windowed); trades page ~100 each, cursor back. We use PnL for label/skill and
  trade tape (up to ~300 newest, ~1-3d for active snipers) for hold times / flip / snipe heuristics.
  Approx balances = net token flow from PnL buy/sell amounts (no USD residual balance endpoint).
"""
import json, os, sys, time, datetime as D, statistics
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib")
import common as C, addr as A
CACHE_H = 6
def _f(x, d=0.0):
    try: return float(x) if x is not None else d
    except Exception: return d
def _ts(s):
    try: return D.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception: return None
def fetch_pnl(addr, mc=None):
    d = C.cg(f"/wallets/{addr}/pnl", {"networks": "solana", "per_page": 300}, mc)
    return ((d or {}).get("data") or {}).get("attributes") or {}
def fetch_trades(addr, mc=None, pages=2, per_page=100):
    out = []; cursor = None
    for _ in range(pages):
        q = {"per_page": per_page}; 
        if cursor: q["cursor"] = cursor
        d = C.cg(f"/networks/solana/wallets/{addr}/trades", q, mc)
        if not d: break
        out += d.get("data") or []; cursor = (d.get("meta") or {}).get("next_cursor")
        if not cursor: break
    return out
def reconstruct(addr, mc=None, window_days=30):
    addr = A.norm(addr, "solana"); pnl = fetch_pnl(addr, mc); trades = fetch_trades(addr, mc)
    tokens = []
    for t in pnl.get("token_stats") or []:
        buy_c, sell_c = int(t.get("total_buy_count") or 0), int(t.get("total_sell_count") or 0)
        buy_amt, sell_amt = _f(t.get("total_buy_token_amount")), _f(t.get("total_sell_token_amount"))
        tokens.append({"address": t.get("address"), "symbol": t.get("symbol"), "name": t.get("name"),
                       "realized_pnl_usd": _f(t.get("realized_pnl_usd")), "unrealized_pnl_usd": _f(t.get("unrealized_pnl_usd")) if t.get("unrealized_pnl_usd") is not None else None,
                       "buy_count": buy_c, "sell_count": sell_c, "buy_usd": _f(t.get("total_buy_usd")), "sell_usd": _f(t.get("total_sell_usd")),
                       "net_token": buy_amt - sell_amt, "avg_buy": _f(t.get("average_buy_price_usd")), "avg_sell": _f(t.get("average_sell_price_usd")),
                       "closed": sell_amt > 0 and abs(buy_amt - sell_amt) / max(buy_amt, 1e-9) < 0.05})
    # trade-tape heuristics (newest first)
    by_tok = {}; holds = []; snipes = 0; flips = 0
    cut = time.time() - window_days * 86400
    for x in trades:
        a = x.get("attributes") or {}; ts = _ts(a.get("block_timestamp"))
        if ts and ts < cut: continue
        tok = a.get("from_token_address") if a.get("kind") == "sell" else a.get("to_token_address")
        e = by_tok.setdefault(tok, {"buys": [], "sells": []})
        e["buys" if a.get("kind") == "buy" else "sells"].append(ts or 0)
    for tok, e in by_tok.items():
        for bt in e["buys"]:
            after = [s for s in e["sells"] if s >= bt]
            if after:
                dt = after[0] - bt; holds.append(dt)
                if dt < 60: snipes += 1
                if dt < 300: flips += 1
    closed = [t for t in tokens if t["closed"]]; wins = [t for t in closed if t["realized_pnl_usd"] > 0]
    win_rate = (len(wins) / len(closed)) if closed else None
    realized = _f(pnl.get("total_realized_pnl_usd"))
    total_tokens = int(pnl.get("total_tokens") or len(tokens))
    buy_n = sum(t["buy_count"] for t in tokens); sell_n = sum(t["sell_count"] for t in tokens)
    med_hold = statistics.median(holds) if holds else None
    trades_per_day = (len(trades) / max(1, window_days)) if trades else 0
    # approx residual balances (token units only; no USD without price)
    approx_bal = [{"address": t["address"], "symbol": t["symbol"], "net_token": t["net_token"]}
                  for t in tokens if t["net_token"] > 1e-6][:30]
    flags = []
    if total_tokens > 500 or trades_per_day > 50: flags.append("bot_volume")
    if snipes >= 5 and (snipes / max(1, len(holds))) > 0.4: flags.append("snipe_heavy")
    if flips >= 8 and med_hold is not None and med_hold < 180: flags.append("flipper")
    if total_tokens <= 3 and buy_n <= 10: flags.append("fresh")
    summary = {"address": addr, "chain": "solana", "window_days": window_days,
               "total_tokens": total_tokens, "realized_pnl": realized,
               "unrealized_pnl": _f(pnl.get("total_unrealized_pnl_usd")),
               "closed_trades": len(closed), "win_rate": round(win_rate, 3) if win_rate is not None else None,
               "buy_count": buy_n, "sell_count": sell_n, "trades_tape": len(trades),
               "median_hold_s": round(med_hold) if med_hold is not None else None,
               "snipe_lt_60s": snipes, "flip_lt_5m": flips, "trades_per_day": round(trades_per_day, 2),
               "flags": flags, "approx_balances": approx_bal,
               "source": "cg_pnl+trades", "limits": "no balances/transfers on solana; PnL is lifetime; trades ~newest 300"}
    return summary, tokens
def label_from(summary):
    flags = set(summary.get("flags") or [])
    if "bot_volume" in flags: return "bot", "high"
    if summary.get("closed_trades", 0) >= 5 and (summary.get("win_rate") or 0) >= 0.6 and (summary.get("realized_pnl") or 0) > 0:
        return "proven_candidate", "low"
    if "snipe_heavy" in flags: return "sniper", "medium"
    if "flipper" in flags: return "flipper", "medium"
    if "fresh" in flags: return "unknown", "low"
    return "unknown", "low"
def upsert_profile(addr, mc=None, force=False):
    """Profile one Solana wallet into wallets.db (+ wallet_history cache). Returns summary."""
    import subprocess
    c = __import__("sqlite3").connect(os.environ.get("WALLETDB", C.BASE + "/wallets.db"), timeout=30)
    c.execute("PRAGMA busy_timeout=30000")
    try: c.execute("""CREATE TABLE IF NOT EXISTS wallet_history(
         address TEXT, chain TEXT, built_at TEXT, window_days INTEGER, summary TEXT, tokens TEXT, PRIMARY KEY(address, chain))""")
    except Exception: pass
    addr = A.norm(addr, "solana")
    if not force:
        r = c.execute("select built_at, summary from wallet_history where address=? and chain='solana'", (addr,)).fetchone()
        if r:
            try:
                age = time.time() - D.datetime.fromisoformat(r[0]).timestamp()
                if age < CACHE_H * 3600: return json.loads(r[1])
            except Exception: pass
    summary, tokens = reconstruct(addr, mc)
    lab, conf = label_from(summary)
    payload = {"wallets": [{"address": addr, "chain": "solana", "chains": "solana", "label": lab, "confidence": conf,
                            "win_rate": summary.get("win_rate"), "realized_pnl": summary.get("realized_pnl"),
                            "total_tokens": summary.get("total_tokens"), "chains_active": 1,
                            "closed_trades": summary.get("closed_trades"),
                            "trades_per_day": summary.get("trades_per_day"),
                            "notes": f"sol profile flags={','.join(summary.get('flags') or [])} hold_med={summary.get('median_hold_s')}s"}]}
    subprocess.run([sys.executable, C.BASE + "/walletdb.py", "upsert"], input=json.dumps(payload),
                   capture_output=True, text=True, timeout=30)
    c.execute("insert or replace into wallet_history values(?,?,?,?,?,?)",
              (addr, "solana", C.now_iso(), summary["window_days"], json.dumps(summary), json.dumps(tokens[:50])))
    c.commit(); c.close(); return summary
def profile_many(addrs, mc=None, max_n=15, workers=6):
    """Parallel (threads); each wallet ~1 pnl + <=2 trade pages = <=3 credits; cached 6h in wallet_history.
    Wallet PnL and trades need the analyst tier or higher. On other plans this returns a skip note and makes no call."""
    if not C.cg_has("wallets"):
        import cgtier
        note = cgtier.unavailable()
        return {A.norm(a, "solana"): {"skipped": note} for a in addrs if a}
    from concurrent.futures import ThreadPoolExecutor
    todo = list(dict.fromkeys(A.norm(x, "solana") for x in addrs if x))[:max_n]; out = {}
    def one(a):
        try: return a, upsert_profile(a, None)
        except Exception as e: return a, {"error": C.redact(e)}
    with ThreadPoolExecutor(workers) as ex:
        for a, r in ex.map(one, todo): out[a] = r
    if mc is not None:
        try:
            with C._CL: C.credit(mc, "rest", 3 * len(todo)); mc.commit()
        except Exception: pass
    return out
if __name__ == "__main__":
    addrs = sys.argv[1:] or json.load(sys.stdin)
    print(json.dumps(profile_many(addrs), indent=1, default=str))
