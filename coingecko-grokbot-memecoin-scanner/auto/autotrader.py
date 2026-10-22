#!/usr/bin/env python3
"""AI AUTONOMOUS paper book — entry engine. Ledger: auto.db (same schema as paper.db + rationale). Human book untouched.
Consumes: market.db discoveries (CG-first deep research), state.json assessed verdicts (AI routine), xfirst queue.
Exits are handled by risk.py running with BOOK=auto PAPER_DB=auto.db (auto/risk_auto.py). AUTO_DRY=1 -> log only.
Secrets from env only (never printed)."""
import os, sys, json, time, sqlite3, datetime as D
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT
os.environ["PAPER_DB"] = f"{BASE}/auto.db"; os.environ["BOOK"] = "auto"
sys.path.insert(0, f"{BASE}/lib"); sys.path.insert(0, f"{BASE}/telegram")
import common as C, core, addr as A, clips as CL
log = C.logger("auto"); DRY = os.environ.get("AUTO_DRY") == "1"
def home(): return os.environ.get("MEMESCAN_HOME") or BASE
def pol_path(): return os.environ.get("MEMESCAN_POLICY") or f"{home()}/auto/policy.json"
def pol(): return json.load(open(pol_path()))
def adb():
    c = core.db(); C.pinit(c); CL.init(c)
    for col in ("rationale text", "tier text", "verdict_source text"):
        try: c.execute(f"alter table trades add column {col}")
        except Exception: pass
    c.executescript("""create table if not exists notices(id integer primary key autoincrement, ts text, text text, sent integer default 0);
      create table if not exists auto_seen(ca text primary key, at text, decision text, tier text, why text);""")
    try:
        import features; features.ensure(c)
    except Exception: pass
    # Cash comes from PAPER_START_CASH (core.db applies it when this book has no trades).
    return c
def f(x, d=0.0):
    try: return float(x)
    except Exception: return d
HARD_WORDS = ("honeypot", "insider heavy", "bot/bundle dominated", "rug", "dev ", "artificial chart", "nsfw", "deployer removed", "of reserve")
def _hp(ws):
    raw = (ws or {}).get("human_participation")
    if raw is None: return None
    try: return float(raw)
    except (TypeError, ValueError): return None
def prepare_policy(P):
    """Runtime defaults for keys added after a policy file was first written."""
    P.setdefault("tiers", {})
    P["tiers"].setdefault("pre_verdict", {"mult": 0.25, "enabled": True})
    P.setdefault("on_ai_discard", "exit")
    return P
def load_ai():
    try: st = json.load(open(f"{home()}/state.json"))
    except Exception: return {}
    out = {}
    for k, v in (st.get("assessed") or {}).items():
        if not v or not v.get("ca"): continue
        net = v.get("network") or k.partition("_")[0]
        out[A.norm(v.get("ca") or "", net)] = v
    return out
def classify(r, P):
    """research dict -> (tier|None, rationale, hard_reason|None).

    An AI discard is never a buy. A buy made before the AI verdict exists is
    tier pre_verdict (small size). Verdict source is stashed on the payload
    as _verdict_source: early | ai.
    """
    P = prepare_policy(P)
    m = r.get("metrics") or {}; tok = r.get("token") or {}; ws = r.get("wallet_score") or {}
    hp = _hp(ws); top10 = f((r.get("holders") or {}).get("top10_pct_ex_pools")); dev = f(tok.get("developer_holding_percentage"))
    fails = list(r.get("fail_reasons") or [])
    ai = (r.get("ai_verdict") or "").strip(); early = (r.get("prelim_verdict") or "").strip()
    source = "ai" if ai else "early"
    r["_verdict_source"] = source; r["_early_label"] = early
    verdict = (ai or early).lower()
    hb = P["hard_block"]
    art = r.get("artificial_chart") or {}
    hp_s = "unknown" if hp is None else f"{hp:.0f}"
    def hard(reason):
        return None, "", reason
    try:
        import liquidity as _LQ
        if _LQ.flagged_nsfw(tok) and _LQ.nsfw_discard(): return hard("nsfw")
    except Exception: pass
    if art.get("band") == "clear" or any("artificial chart" in str(x).lower() for x in fails):
        return hard("artificial chart: " + "; ".join(art.get("reasons") or ["engineered price action"]))
    if tok.get("is_honeypot") is True: return hard("honeypot")
    if top10 > hb["top10_pct"]: return hard(f"top10 {top10:.0f}%")
    if dev > hb["dev_pct"]: return hard(f"dev {dev:.0f}%")
    if m.get("liq", 0) < hb["min_liq"]: return hard(f"liq ${m.get('liq',0):,.0f}")
    if any(w in " ".join(fails).lower() for w in HARD_WORDS): return hard("; ".join(fails))
    if ws.get("read") in ("bot/bundle dominated", "insider heavy"): return hard(ws["read"])
    if hp is not None and hp < hb["min_human"] and "unverified" not in " ".join(fails): return hard(f"human {hp}")
    if "bundle in top10" in fails: return hard("bundle in top10")
    if ai.lower().startswith("discard"): return hard("AI discard")
    why = f"score {r.get('score')} · human {hp_s} · buyers/h {m.get('buyers_h1')} · h1 {m.get('h1_change',0):+.0f}% · flow {r.get('flow_buy_share')} · liq ${m.get('liq',0):,.0f}"
    if source == "ai":
        if verdict.startswith("organic"): return "organic", "Organic Hype · " + why, None
        if verdict.startswith("watch") and f(r.get("score")) >= P.get("watch_min_score", 65) and hp is not None and hp >= P.get("watch_min_human", 45):
            return "watch", "Watch · " + why, None
        if verdict.startswith("scout"): return "scout", "Scout · " + why, None
        return None, "", None
    label = None
    if verdict.startswith("organic"): label = "Early " + (early or "organic")
    elif verdict.startswith("watch") and f(r.get("score")) >= P.get("watch_min_score", 65) and hp is not None and hp >= P.get("watch_min_human", 45):
        label = "Early " + (early or "watch")
    else:
        s = P["scout"]   # degen scout: strong momentum + acceptable wallet mix despite soft discard
        soft = all(any(k in x for k in ("unverified", "score", "human", "single")) for x in fails) if fails else True
        if soft and f(m.get("h1_change")) >= s["min_h1_change"] and (m.get("buyers_h1") or 0) >= s["min_buyers_h1"] and f(r.get("flow_buy_share")) >= s["min_flow_buy_share"] \
           and (hp is None or hp >= s["min_human"] or "unverified" in " ".join(fails)) and f(r.get("score")) >= s["min_score"] and m.get("liq", 0) >= s["min_liq"] and f(m.get("m5_change")) >= 0:
            label = "Early scout (soft discard: " + ("; ".join(fails) or "none") + ")"
    if not label or not P["tiers"].get("pre_verdict", {}).get("enabled", True): return None, "", None
    return "pre_verdict", label + " · " + why, None
def candidates(P):
    out = []; cut = (D.datetime.now(C.MYT) - D.timedelta(minutes=P["max_candidate_age_min"])).isoformat(timespec="seconds")
    ai = load_ai()
    mc = sqlite3.connect(f"file:{home()}/market.db?mode=ro", uri=True, timeout=10)
    for key, ca, net, pool, payload, seen in mc.execute("select key, ca, network, pool, payload, seen_at from discoveries where stage like 'deep:%' and payload is not null and seen_at>=?", (cut,)):
        try: r = json.load(open(payload))
        except Exception: continue
        a = ai.get(A.norm(ca, net))
        if a and (a.get("verdict") or "").strip():
            r["ai_verdict"] = a.get("verdict"); r["ai_reason"] = a.get("rule") or a.get("reason") or ""
        else:
            r["ai_verdict"] = None
        r["_src"] = "cg-first"; out.append(r)
    mc.close()
    try:
        for q in json.load(open(f"{home()}/xfirst/queue.json")):
            if q.get("status") in ("pending", "done") and q.get("payload_file") and (q.get("queued_at") or "") >= cut:
                pf = q["payload_file"] if q["payload_file"].startswith("/") else f"{BASE}/{q['payload_file']}"
                r = json.load(open(pf)); r["prelim_verdict"] = q.get("prelim_verdict") or r.get("prelim_verdict"); r["_src"] = "x-first"; out.append(r)
    except Exception: pass
    return out
def taxes(r):
    """buy/sell tax fractions from any *tax* fields in token info / gt_score_details (CG/GT expose them on some chains)."""
    bt = st = 0.0
    def walk(o):
        nonlocal bt, st
        if isinstance(o, dict):
            for k, v in o.items():
                kl = k.lower()
                if "buy_tax" in kl: bt = max(bt, f(v) / (100 if f(v) > 1 else 1))
                elif "sell_tax" in kl: st = max(st, f(v) / (100 if f(v) > 1 else 1))
                else: walk(v)
    walk(r.get("token") or {}); return min(bt, 0.5), min(st, 0.5)
def size(c, r, tier, P):
    import sizing
    m = r.get("metrics") or {}; liq = m.get("liq") or 0
    rows = core.mtm(c); cash = core.cash(c); pv = sum((x["value"] or x["cost_usd"]) for x in rows); eq = cash + pv
    if len(rows) >= P["max_positions"]: return 0, "max positions"
    if pv >= eq * P["max_exposure_pct"] / 100: return 0, "max exposure"
    if sum(1 for x in rows if x["network"] == r["network"]) >= P["max_per_chain"]: return 0, f"{r['network']} cap"
    base = eq * P["base_pct_of_equity"] / 100 * P["tiers"][tier]["mult"]
    try:
        tag = {"organic": "Organic Hype", "watch": "Watch", "scout": "Watch", "pre_verdict": "Watch"}.get(tier, "Watch")
        sz = sizing.recommend(r["network"], r["pool"], tag, "high" if tier == "organic" else "low", r.get("score"), (r.get("wallet_score") or {}).get("human_participation"),
                              r.get("bundles_n") or 0, 0, liq)
        if sz.get("rec"): base = min(base, sz["rec"] * P["tiers"][tier]["mult"] / P["tiers"]["organic"]["mult"])   # pool-median sizing × conviction
    except Exception: pass
    usd = min(base, eq * P["max_pct_of_equity_per_pos"] / 100, liq * P["max_liq_pct"] / 100, P["max_usd"], cash * 0.9)
    if (r.get("token") or {}).get("is_honeypot") is None: usd *= P["honeypot_unknown_haircut"]
    return (round(usd, 2), "ok") if usd >= P["min_usd"] else (0, f"size ${usd:.0f} < min")
def cooled(c, sym, P):
    cut = (D.datetime.now(C.MYT) - D.timedelta(minutes=P["ticker_cooldown_min"])).isoformat(timespec="seconds")
    return c.execute("select 1 from trades where lower(symbol)=? and ts>=? limit 1", ((sym or "").lower(), cut)).fetchone() is None
def note(c, text): c.execute("insert into notices(ts,text) values(?,?)", (C.now_iso(), text)); c.commit()
def enter(c, r, tier, why, P):
    ca = A.norm(r["ca"], r["network"]); sym = (r.get("token") or {}).get("symbol") or "?"
    if c.execute("select 1 from positions where ca=?", (ca,)).fetchone(): return "held"
    if not cooled(c, sym, P): return "cooldown"
    import entryfilters as F; EF = P.get("entry_filters", {})
    tok = r.get("token") or {}; buzz = F.ca_buzz(ca); r["_buzz"] = buzz
    imp = F.impersonation(tok.get("name"), sym)
    if imp and buzz["authors"] < 1: return f"HARD impersonation ({imp}) without exact-CA X buzz"
    if tier in ("watch", "scout") and buzz["authors"] < EF.get("min_ca_buzz_authors", 1):
        return "wait:no exact-CA X buzz (ticker-only buzz doesn't count)"
    age = (r.get("metrics") or {}).get("age_min") or 0
    try: age += (time.time() - D.datetime.fromisoformat(r["generated_at"]).timestamp()) / 60
    except Exception: pass
    if age < EF.get("min_pool_age_min", 10): return f"wait:fragile pool age {age:.0f}m < {EF.get('min_pool_age_min', 10)}m"
    # live pre-trade check: research can be minutes old and pools get pulled; never enter on stale liquidity
    q = core.quote(ca, r["network"]); rl = (r.get("metrics") or {}).get("liq") or 0
    if not q or not q.get("liquidity") or q["liquidity"] < max(P["hard_block"]["min_liq"], P.get("min_live_liq_ratio", 0.5) * rl):
        return f"liq gone (live ${(q or {}).get('liquidity') or 0:,.0f} vs research ${rl:,.0f})"
    if q.get("pool") and not A.same(q["pool"], r["pool"]) and q["liquidity"] < rl * 0.8: return "pool mismatch"
    r.setdefault("metrics", {})["liq"] = min(rl, q["liquidity"]) if rl else q["liquidity"]
    fr = F.fragile(age, q["liquidity"], EF.get("min_pool_age_min", 10), EF.get("min_live_liq", 10000))
    if fr: return "wait:fragile " + fr
    pf = F.profile(r["network"], r["pool"]); r["_profile"] = pf; W = EF.get("winner_profile", {})
    if pf["score"] < W.get("min_score", 0.5) or pf["nondust_trades_10m"] < W.get("min_nondust_trades_10m", 15) or pf["nondust_vol_10m"] < W.get("min_nondust_vol_10m", 3000) \
       or (pf["bars"] >= 4 and pf["largest_bar_share_of_gain"] > W.get("max_single_bar_share", 0.6)):
        return f"wait:profile {pf['score']} (trades {pf['nondust_trades_10m']}, vol ${pf['nondust_vol_10m']:,}, green {pf['green_share']}, spike {pf['largest_bar_share_of_gain']})"
    usd, sw = size(c, r, tier, P)
    if not usd: return sw
    pm = W.get("size_base", 0.7) + W.get("size_slope", 0.6) * pf["score"]   # weight toward winner profile (0.7x .. 1.3x)
    usd = round(min(usd * pm, (r.get("metrics") or {}).get("liq", 0) * P["max_liq_pct"] / 100, P["max_usd"]), 2)
    bt, stx = taxes(r)
    if DRY: log("DRY ENTER", tier, sym, r["network"], f"${usd}", why); return "dry"
    out = core.buy(c, ca, usd, chain=r["network"], source=f"auto:{tier}", prefer_ca=ca)
    if not out.startswith("🟢"): log("buy fail", sym, out[:120]); return "buyfail"
    if bt or stx:   # token taxes: buy tax now, sell tax pre-haircut on qty (conservative)
        c.execute("update positions set qty=qty*? where ca=?", ((1 - bt) * (1 - stx), ca))
    src = r.get("_verdict_source") or "early"
    rat = f"[{r.get('_src')}|{src}] {why} · CA-buzz {buzz['authors']} authors · profile {pf['score']} (trades {pf['nondust_trades_10m']}, green {pf['green_share']}, spike {pf['largest_bar_share_of_gain']}) ×{pm:.2f}" + (f" · tax b{bt*100:.0f}%/s{stx*100:.0f}%" if bt or stx else "") + (" · honeypot unknown → ½ size" if (r.get("token") or {}).get("is_honeypot") is None else "")
    c.execute("update trades set rationale=?, tier=?, tag=?, verdict_source=? where id=(select max(id) from trades where ca=? and side='buy')", (rat, tier, tier, src, ca))
    c.execute("update positions set entry_tag=? where ca=?", (tier, ca))
    try:
        import features
        bid = c.execute("select id, fill_price from trades where ca=? and side='buy' order by id desc limit 1", (ca,)).fetchone()
        features.snapshot_trade(c, r, tier, src, why, bid["id"] if bid else None, entry_px=(bid["fill_price"] if bid else None))
    except Exception as e: log("features", C.redact(e))
    c.commit()
    CL.meta(c, ca)   # auto_clip=1 for BOOK=auto
    log("ENTER", tier, sym, r["network"], f"${usd}", rat); note(c, f"🤖🟢 <b>AI book entered</b> {core.esc(sym)} ({r['network']}) ${usd:,.0f} · {tier}\n{core.esc(rat)[:300]}")
    return "entered"
LASTN = [0]
def flush_notices(c, P):
    ab = C.risk_cfg().get("auto_book", {})   # on/off lives in risk.json (auto_book.notify)
    if not ab.get("notify", P["notify"]["enabled"]) or DRY: return
    if time.time() - LASTN[0] < ab.get("notify_min_interval_s", P["notify"]["min_interval_s"]): return
    rows = c.execute("select id, text from notices where sent=0 order by id").fetchall()
    if not rows: return
    own = core.owner()
    if not own: return
    txt = rows[0]["text"] if len(rows) == 1 else "🤖 <b>AI book digest</b> (" + str(len(rows)) + ")\n\n" + "\n\n".join(r["text"][:350] for r in rows[:8]) + ("\n…" if len(rows) > 8 else "")
    if core.send(own["chat_id"], txt[:4000]).get("ok"):
        c.executemany("update notices set sent=1 where id=?", [(r["id"],) for r in rows]); c.commit(); LASTN[0] = time.time()
def reconcile(c, P):
    """Early entries wait for the AI verdict. Discard exits, or is kept and marked, per on_ai_discard."""
    P = prepare_policy(P)
    mode = (P.get("on_ai_discard") or "exit").strip().lower()
    if mode not in ("exit", "keep"): mode = "exit"
    ai = load_ai()
    if not ai: return 0
    import features
    n = 0
    for p in c.execute("select * from positions").fetchall():
        if (p["entry_tag"] or "") != "pre_verdict": continue
        a = ai.get(A.norm(p["ca"], p["network"]))
        if not a or not (a.get("verdict") or "").strip(): continue
        row = c.execute("select ai_later from trade_features where ca=? and kind='trade' and exit_ts is null order by id desc limit 1", (p["ca"],)).fetchone()
        if row and row["ai_later"]: continue
        v = a.get("verdict").strip(); reason = a.get("rule") or a.get("reason") or ""
        if not v.lower().startswith("discard"):
            features.note_ai(c, p["ca"], v, reason, disagreed=False); c.commit(); continue
        if mode == "keep":
            features.note_ai(c, p["ca"], v, reason, disagreed=True)
            note(c, f"🤖 <b>AI disagreed</b> — keeping {core.esc(p['symbol'])} ({p['network']})\n{core.esc(reason)[:240]}")
            c.commit(); n += 1; continue
        out = core.sell(c, p["ca"], "all", source="ai-discard")
        if not str(out).startswith("🔴"):
            log("AI discard exit failed", p["symbol"], (out or "")[:120]); continue
        features.record_exit(c, p["ca"], "AI discard: " + str(reason)[:240], "ai-discard")
        src = c.execute("select verdict_source from trades where ca=? and side='buy' and verdict_source is not null order by id desc limit 1", (p["ca"],)).fetchone()
        if src and src[0]:
            c.execute("update trades set verdict_source=? where id=(select max(id) from trades where ca=? and side='sell')", (src[0], p["ca"]))
        c.commit()
        log("AI discard exit", p["symbol"], (out or "")[:120])
        note(c, f"🤖🔴 <b>AI discard exit</b> {core.esc(p['symbol'])} ({p['network']})\n{core.esc(str(reason))[:240]}")
        n += 1
    return n
def tune_due(P, hours=6):
    """True when the tuner has not been run in `hours`. Reads the on-disk check time, not process memory."""
    s = (P or {}).get("last_tune_check") or ""
    if not s: return True
    try: return time.time() - D.datetime.fromisoformat(s).timestamp() >= hours * 3600
    except Exception: return True
def cycle(c):
    P = prepare_policy(pol()); n = 0; rank = {"organic": 0, "watch": 1, "pre_verdict": 2, "scout": 3}
    try: reconcile(c, P)
    except Exception as e: log("reconcile", C.redact(e))
    cl = []
    for r in candidates(P):
        t = classify(r, P); cl.append((rank.get(t[0], 3), -f(r.get("score")), id(r), r, t))
    for _, _, _, r, (tier, why, hard) in sorted(cl):
        ca = A.norm(r.get("ca") or "", r.get("network"))
        if not ca or c.execute("select 1 from auto_seen where ca=? and decision in ('entered','skip-hard','skip')", (ca,)).fetchone(): continue
        if c.execute("select 1 from auto_seen where ca=? and decision like 'wait:%' and at>?", (ca, (D.datetime.now(C.MYT) - D.timedelta(seconds=120)).isoformat(timespec="seconds"))).fetchone(): continue
        if hard: dec = "skip-hard"; why = hard
        elif not tier or not (P.get("tiers") or {}).get(tier, {}).get("enabled"): dec = "skip"; why = why or "no tier"
        else: dec = enter(c, r, tier, why, P)
        if dec.startswith("HARD "): log("skip", ca[:10], dec); why = dec; dec = "skip-hard"
        if dec.startswith("wait:"): why = dec
        if dec.startswith("liq gone") or dec == "pool mismatch": log("skip", ca[:10], dec); why = dec; dec = "skip-hard"
        if dec in ("skip", "skip-hard"):
            try:
                import features
                features.snapshot_skip(c, r, dec, why, r.get("_verdict_source"))
            except Exception as e: log("features", C.redact(e))
        if dec in ("cooldown", "max positions", "max exposure") or dec.endswith("cap") or dec == "dry": pass  # retry later
        c.execute("insert or replace into auto_seen values(?,?,?,?,?)", (ca, C.now_iso(), dec if dec != "dry" else "dry", tier, (why or "")[:300])); c.commit()
        if dec == "entered": n += 1
    return n
def main():
    C.start_heartbeat(log)
    log("start", "DRY" if DRY else "RUN (paper)"); c = adb(); beat = 0
    while True:
        try:
            n = cycle(c); flush_notices(c, pol())
            if tune_due(pol()):
                import subprocess; subprocess.run([sys.executable, f"{BASE}/auto/tuner.py"], timeout=60)
        except Exception as e: log("cycle err", C.redact(e)); n = -1
        if time.time() - beat > 60:
            log("heartbeat open", c.execute("select count(*) from positions").fetchone()[0], "cash", round(core.cash(c), 2)); beat = time.time()
        time.sleep(10)
if __name__ == "__main__":
    if "--once" in sys.argv: c = adb(); print("entered", cycle(c))
    else: main()
