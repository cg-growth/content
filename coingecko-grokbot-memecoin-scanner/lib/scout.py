"""SCOUT tier (near-miss) for the HUMAN book alert flow. Same logic family as the AI book's degen-scout tier.
Scout = deep-research DISCARD whose fail reasons are ALL soft, with strong momentum. Never on hard reasons.
Thresholds: risk.json "scout" (defaults below). Caps/dedupe state in scout.db (own WAL file)."""
import json, sqlite3, time, re
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT
DEF = {"min_score": 55, "min_human": 50, "min_h1_change": 15, "min_buyers_h1": 40, "min_flow_buy_share": 0.55, "min_m5_change": 0,
       "min_live_liq": 10000, "min_pool_age_min": 10, "max_age_min": 720, "cards_per_hour": 3, "forwards_per_hour": 6, "size_mult": 0.4,
       "hard_top10_pct": 60, "max_bundled_top_pct": 15.0, "hard_dev_pct": 20, "hard_min_human": 30, "min_avg_trade_usd": 3.0}
SOFT = ("bundle in top10", "human ", "unverified wallets", "single-author", "single author", "score ")
HARD_FAIL = ("honeypot", "top10 ", "dev ", "bot/bundle dominated", "insider heavy", "rug", "wash", "dust", "copycat", "namesake",
             "nsfw", "deployer removed", "of reserve")
def cfg():
    try: return {**DEF, **(json.load(open(f"{BASE}/risk.json")).get("scout") or {})}
    except Exception: return DEF
def f(x, d=0.0):
    try: return float(x)
    except Exception: return d
def classify(r, ca_buzz=None, namesakes=0):
    """r = research payload (research/<net>_<ca>.json). -> (is_scout, caveats[list], hard_reason|None)"""
    k = cfg(); m = r.get("metrics") or {}; tok = r.get("token") or {}; ws = r.get("wallet_score") or {}
    fails = list(r.get("fail_reasons") or []); hp = f(ws.get("human_participation")); score = f(r.get("score"))
    top10 = f((r.get("holders") or {}).get("top10_pct_ex_pools")); dev = f(tok.get("developer_holding_percentage"))
    unverified = any("unverified" in x for x in fails)
    # hard blocks (never Scout)
    if tok.get("is_honeypot") is True: return False, [], "honeypot"
    if top10 > k["hard_top10_pct"]: return False, [], f"top10 {top10:.0f}%"
    if dev > k["hard_dev_pct"]: return False, [], f"dev {dev:.0f}%"
    if ws.get("read") in ("bot/bundle dominated", "insider heavy"): return False, [], ws["read"]
    if hp and hp < k["hard_min_human"] and not unverified: return False, [], f"bot farm (human {hp:.0f} < {k['hard_min_human']})"
    bpct = bundled_top_pct(r)
    if "bundle in top10" in fails:
        if bpct > k["max_bundled_top_pct"]: return False, [], f"bundles hold {bpct:.1f}% of top10 (> {k['max_bundled_top_pct']}%)"
    hf = [x for x in fails if x != "bundle in top10" and any(h in x.lower() for h in HARD_FAIL)]
    if hf: return False, [], "; ".join(hf)
    trades = (m.get("buys_h1") or 0) + (m.get("sells_h1") or 0)
    if trades and f(m.get("vol_h1")) / trades < k["min_avg_trade_usd"]: return False, [], f"dust/wash (avg trade ${f(m.get('vol_h1'))/trades:.2f})"
    if ca_buzz == 0 and namesakes: return False, [], "namesake/copycat with 0 CA buzz"
    try:   # same hard block as the AI book: stock/brand/celebrity impersonation unless X has posts on the exact CA
        import entryfilters as F
        imp = F.impersonation(tok.get("name"), tok.get("symbol"))
        if imp and not (ca_buzz or F.ca_buzz(r.get("ca") or "")["authors"]): return False, [], f"impersonation ({imp}) without exact-CA buzz"
    except Exception: pass
    if (m.get("age_min") or 0) > k["max_age_min"]: return False, [], f"old token ({m.get('age_min')}m)"
    # soft-only + strong momentum
    if not fails: return False, [], None          # not a near-miss (would be Watch/Organic)
    if not all(any(s in x.lower() for s in SOFT) for x in fails): return False, [], None
    need = [(score >= k["min_score"], f"score {score} < {k['min_score']}"), (hp >= k["min_human"] or unverified, f"human {hp} < {k['min_human']}"),
            (f(m.get("h1_change")) >= k["min_h1_change"], "weak h1"), ((m.get("buyers_h1") or 0) >= k["min_buyers_h1"], "few buyers"),
            (f(r.get("flow_buy_share")) >= k["min_flow_buy_share"], "sell flow"), (f(m.get("m5_change")) >= k["min_m5_change"], "m5 fading"),
            (f(m.get("liq")) >= k["min_live_liq"], "liq < min")]
    if not all(ok for ok, _ in need): return False, [], None
    cav = []
    for x in fails:
        mm = re.match(r"human ([\d.]+)", x)
        if mm: cav.append(f"human score {mm.group(1)} < {cfg_deep_min_human()}")
        elif x == "bundle in top10": cav.append(f"bundled wallets in top holders ({bpct:.1f}% of supply)")
        elif "unverified" in x: cav.append("wallets unverified (mostly unknown to wallet DB)")
        else: cav.append(x)
    if r.get("buzz") and (r["buzz"].get("unique_authors") or 0) <= 1: cav.append("single-author buzz")
    return True, cav, None
def bundled_top_pct(r):
    ws = r.get("wallet_score") or {}; members = {a.lower() for b in (ws.get("bundles") or []) for a in b.get("members") or []}
    return sum(f(h.get("pct")) for h in ((r.get("holders") or {}).get("top") or [])[:10] if (h.get("a") or "").lower() in members)
def cfg_deep_min_human():
    try: return json.load(open(f"{BASE}/risk.json"))["discovery"]["deep_min_human"]
    except Exception: return 60
def live_liq_ok(ca, net):
    import sys; sys.path.insert(0, f"{BASE}/telegram"); sys.path.insert(0, f"{BASE}/lib"); import core
    q = core.quote(ca, net); l = (q or {}).get("liquidity") or 0
    return l >= cfg()["min_live_liq"], l
def _db():
    c = sqlite3.connect(f"{BASE}/scout.db", timeout=10); c.execute("pragma journal_mode=wal"); c.execute("pragma busy_timeout=10000")
    c.execute("create table if not exists events(ca text, at real, kind text, src text, primary key(ca, kind))"); return c
def seen(ca):
    c = _db(); r = c.execute("select 1 from events where ca=? limit 1", (ca,)).fetchone(); c.close()
    if r: return True
    try:   # never re-alert a token already carded in the human book
        p = sqlite3.connect(f"file:{BASE}/paper.db?mode=ro", uri=True, timeout=5); a = p.execute("select 1 from alerts where ca=? limit 1", (ca,)).fetchone(); p.close()
        return bool(a)
    except Exception: return False
def allow(ca, kind):
    """kind 'forward' (discovery/xfirst -> routine) or 'card' (send_card). Dedupe per CA + hourly cap."""
    k = cfg(); c = _db()
    if c.execute("select 1 from events where ca=? and kind=?", (ca, kind)).fetchone(): c.close(); return False, "dup"
    n = c.execute("select count(*) from events where kind=? and at>?", (kind, time.time() - 3600)).fetchone()[0]; c.close()
    cap = k["cards_per_hour"] if kind == "card" else k["forwards_per_hour"]
    return (n < cap), (f"cap {n}/{cap}h" if n >= cap else "ok")
def mark(ca, kind, src=""):
    c = _db(); c.execute("insert or ignore into events values(?,?,?,?)", (ca, time.time(), kind, src)); c.commit(); c.close()
