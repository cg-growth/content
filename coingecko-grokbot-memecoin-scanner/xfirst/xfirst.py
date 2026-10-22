#!/usr/bin/env python3
"""X-first discovery (reverse workflow). The agent runs X searches (X MCP is agent-only) and saves the raw results
to xfirst/inbox/*.txt|json; this script does everything else:
  extract CAs (EVM 0x / Solana base58) + cashtags -> buzz quality score (unique authors, engagement, shill/CA-drop
  patterns, duplicate text, copycat tickers) -> dedupe vs state.json / discoveries (50% growth recheck rule) ->
  resolve CA on CoinGecko onchain (/search/pools, CA-first; chains from risk.json discovery.networks,
  or xfirst.networks when set) -> same pool gates as
  discovery (age relaxed, see risk.json "xfirst") -> deep research via discovery._deep (wallet DB scoring, no forward)
  -> ranked candidates JSON + top N queued (source "x-first", X post links attached) into pending_research.json.
Usage:
  xfirst.py run [files...]        (default: all files in xfirst/inbox; processed files move to xfirst/runs/<ts>/)
      --no-deep   resolve + gate only (no deep research / queueing)     --top N  max deep+queue (default 3)
  xfirst.py done <ca>             mark a queued x-first item handled
  xfirst.py queue                 show the x-first queue
Secrets: COINGECKO_DEMO_API_KEY or COINGECKO_PRO_API_KEY from env only (via lib/common.py); never printed."""
import json, os, re, sys, time, glob, shutil, datetime as D, collections
os.environ["DISCOVERY_DRY"] = "1"          # reuse discovery deep research without webhook forwards
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT; XF = BASE + "/xfirst"; QUEUE = XF + "/queue.json"
sys.path.insert(0, BASE + "/lib"); sys.path.insert(0, BASE + "/discovery"); import common as C, addr as A, utm
def nets():
    """Chains X-first will resolve. xfirst.networks overrides discovery.networks."""
    cfg = C.risk_cfg()
    chosen = (cfg.get("xfirst") or {}).get("networks") or (cfg.get("discovery") or {}).get("networks") or []
    return list(chosen)
EVM = re.compile(r"(?<![0-9a-zA-Z])0x[a-fA-F0-9]{40}(?![0-9a-fA-F])")
SOL = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z/=.])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])")
CASH = re.compile(r"(?<![\w$])\$([A-Za-z][A-Za-z0-9_]{1,14})\b")
SHILL = [r"\bDM\b.{0,20}(VIP|access|me)", r"\bVIP\b", r"private (TG|telegram|group)", r"join (my|our) (TG|telegram)", r"\b\d{2,4}x\b", r"\$\d+K?\s*(→|->|to)\s*\$\d+", r"100x|1000x",
         r"next (100x|gem)", r"don'?t miss", r"\bsend it\b", r"🚀{3,}", r"giveaway|airdrop", r"\bNFA\b.*\bDYOR\b", r"gem alert", r"low ?cap gem", r"get in (now|early)"]
MAJORS = {"BTC", "ETH", "SOL", "BNB", "USDT", "USDC", "XRP", "DOGE", "HYPE", "BASE", "SUI", "PEPE", "TRUMP", "ADA", "TON", "AVAX", "LINK", "ZORA", "VIRTUAL", "AI", "CA"}
def now(): return D.datetime.now(C.MYT)
def f(x, d=0.0):
    try: return float(x)
    except Exception: return d
# ---------- input ----------
def load_blobs(path):
    """Accept raw MCP result text (wrapper + JSON line), a single X API JSON object, or a list of them / simple posts."""
    txt = open(path, encoding="utf-8", errors="replace").read(); out = []
    try: j = json.loads(txt); out = j if isinstance(j, list) else [j]
    except Exception:
        for line in txt.splitlines():
            line = line.strip()
            if line.startswith("{") and '"data"' in line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out
def posts_from(blobs, src):
    posts = []
    for b in blobs:
        if "text" in b and "data" not in b: b = {"data": [b]}      # simple post object
        users = {u["id"]: u for u in ((b.get("includes") or {}).get("users") or [])}
        for p in b.get("data") or []:
            u = users.get(p.get("author_id"), {}); upm = u.get("public_metrics") or {}
            posts.append({"id": str(p.get("id")), "text": p.get("text") or "", "url": p.get("url") or (f"https://x.com/{u.get('username','i')}/status/{p.get('id')}"),
                          "author_id": p.get("author_id") or p.get("author"), "username": u.get("username") or p.get("author"), "created_at": p.get("created_at"),
                          "followers": upm.get("followers_count", p.get("followers")), "following": upm.get("following_count"), "acct_created": u.get("created_at"),
                          "verified": u.get("verified"), "pm": p.get("public_metrics") or p.get("metrics") or {},
                          "cashtags": [c["tag"].upper() for c in ((p.get("entities") or {}).get("cashtags") or [])], "query_file": os.path.basename(src)})
    return posts
# ---------- extraction + buzz ----------
def extract(text):
    t = re.sub(r"https?://\S+", " ", text)
    evm = {m.lower() for m in EVM.findall(t)}; t = EVM.sub(" ", t)
    sol = {m for m in SOL.findall(t) if not m.startswith("0x") and re.search(r"\d", m) and re.search(r"[a-z]", m) and re.search(r"[A-Z]", m)}
    return evm, sol, {c.upper() for c in CASH.findall(text)}
def shill_hits(text): return [p for p in SHILL if re.search(p, text, re.I)]
def norm(text): return re.sub(r"[^a-z]", "", re.sub(r"https?://\S+|\$\w+|0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44}", "", text.lower()))[:160]
def author_q(p):
    fol = f(p.get("followers")); fing = f(p.get("following")); age_d = None
    if p.get("acct_created"):
        try: age_d = (now() - D.datetime.fromisoformat(p["acct_created"].replace("Z", "+00:00"))).days
        except Exception: pass
    q = min(1.0, (fol / 5000) ** 0.5) if fol else 0.1
    if age_d is not None and age_d < 60: q *= 0.4
    if fing and fol and fing > fol * 3: q *= 0.6
    return round(q, 3), age_d
def buzz(group, ticker_cas):
    """group: posts mentioning one CA -> buzz dict with score 0..100 (100 = broad, organic, engaged)."""
    authors = {}; eng = imp = 0; shill_posts = 0; texts = collections.Counter(); flags = set()
    for p in group:
        pm = p["pm"]; e = f(pm.get("like_count")) + 2 * f(pm.get("retweet_count")) + f(pm.get("reply_count")) + 2 * f(pm.get("quote_count")); eng += e; imp += f(pm.get("impression_count"))
        aq, age_d = author_q(p); authors.setdefault(p["author_id"], {"user": p["username"], "q": aq, "age_d": age_d, "followers": p.get("followers"), "posts": 0})["posts"] += 1
        sh = shill_hits(p["text"])
        if sh: shill_posts += 1
        if re.search(r"\bCA\b\s*[:：]", p["text"]) and len(p["text"]) < 140: flags.add("bare CA drop")
        texts[norm(p["text"])] += 1
    n, ua = len(group), len(authors)
    dup = sum(c for c in texts.values() if c > 1) / max(1, n)
    shill = shill_posts / max(1, n); top_share = max(a["posts"] for a in authors.values()) / n
    if dup >= 0.4: flags.add(f"copy-paste text {dup:.0%}")
    if shill >= 0.5: flags.add(f"shill/VIP phrasing {shill:.0%}")
    if top_share >= 0.6 and n >= 3: flags.add(f"one account = {top_share:.0%} of posts")
    if any(len(v) > 1 for v in ticker_cas.values()): flags.add("copycat ticker (same $TICKER, multiple CAs)")
    fresh = sum(1 for a in authors.values() if a["age_d"] is not None and a["age_d"] < 60) / ua
    if fresh >= 0.5: flags.add(f"fresh accounts {fresh:.0%}")
    aqs = sum(a["q"] for a in authors.values())
    s = (min(35, ua * 7) + min(25, (eng ** 0.5) * 2.5) + min(20, aqs * 10) + min(10, (imp ** 0.5) / 10)
         - 30 * shill - 20 * dup - 15 * max(0, top_share - 0.5) - 15 * fresh - (10 if any(len(v) > 1 for v in ticker_cas.values()) else 0))
    s = round(max(0, min(100, s + 10)), 1)
    grade = "organic" if s >= 55 and shill < 0.4 else "mixed" if s >= 30 else "shill/thin"
    return {"score": s, "grade": grade, "posts": n, "unique_authors": ua, "engagement": round(eng), "impressions": round(imp), "shill_share": round(shill, 2),
            "dup_share": round(dup, 2), "fresh_author_share": round(fresh, 2), "top_author_share": round(top_share, 2), "flags": sorted(flags),
            "authors": sorted(authors.values(), key=lambda a: -a["q"])[:8]}
# ---------- dedupe ----------
def seen_index():
    try: st = json.load(open(BASE + "/state.json"))
    except Exception: st = {}
    idx = {}
    for sect in ("assessed", "pending"):
        for k, v in (st.get(sect) or {}).items():
            net = k.partition("_")[0]; ca = A.norm(v.get("ca") or "", net)
            rec = {"key": k, "sect": sect, "verdict": v.get("verdict"), "metrics": v.get("metrics") or {}, "at": v.get("at")}
            idx[k] = rec
            if ca: idx.setdefault(ca, rec)
    mc = C.mdb()
    for r in mc.execute("select key, ca, stage, buyers, liq, seen_at, network from discoveries"):
        net = r[6] or r[0].partition("_")[0]; ca = A.norm(r[1] or "", net)
        rec = {"key": r[0], "sect": "discoveries", "verdict": r[2], "metrics": {"buyers": r[3], "liq": r[4]}, "at": r[5]}
        idx.setdefault(r[0], rec)
        if ca: idx.setdefault(ca, rec)
    for q in load_queue():
        ca = A.norm(q["ca"], q.get("network")); idx.setdefault(ca, {"key": q["key"], "sect": "xfirst-queue", "verdict": "queued", "metrics": {}, "at": q["queued_at"]})
    return idx
def grown(prev, m):
    pb, pl = f(prev.get("buyers") or prev.get("buyers_h1")), f(prev.get("liq"))
    return (pb and f(m.get("buyers_h1")) >= pb * 1.5) or (pl and f(m.get("liq")) >= pl * 1.5)
# ---------- resolve ----------
def resolve(ca, mc):
    """CA-first: /search/pools across networks -> pools whose base or quote token == CA on supported networks."""
    r = C.cg("/search/pools", {"query": ca, "page": 1}, mc) or {}; out = []
    for p in r.get("data") or []:
        net = p["id"].partition("_")[0]; rel = p.get("relationships") or {}
        bt = (rel.get("base_token") or {}).get("data", {}).get("id", ""); qt = (rel.get("quote_token") or {}).get("data", {}).get("id", "")
        if net not in nets(): continue
        if A.same(bt.partition("_")[2], ca): out.append(p)
    return sorted(out, key=lambda p: -f(p["attributes"].get("reserve_in_usd")))
def gate_cfg():
    k = dict(C.risk_cfg()["discovery"]); k.update({"max_age_hours": 72, "min_buyers_h1": 15, "max_h1_change_pct": 5000, "min_h1_change_pct": -60})
    k.update(C.risk_cfg().get("xfirst") or {}); return k
# ---------- queue ----------
def load_queue():
    try: return json.load(open(QUEUE))
    except Exception: return []
def save_queue(q):
    tmp = QUEUE + ".tmp"; json.dump(q, open(tmp, "w"), indent=1); os.replace(tmp, QUEUE)
    try: import fwdq; fwdq.write_pending()
    except Exception as e: print("pending mirror err", C.redact(e))
# ---------- main ----------
def run(files, deep=True, top=3):
    t0 = time.time(); ts = now().strftime("%Y%m%d_%H%M%S"); files = files or sorted(glob.glob(XF + "/inbox/*"))
    posts = {}
    for fp in files:
        for p in posts_from(load_blobs(fp), fp): posts.setdefault(p["id"], p)
    posts = list(posts.values()); by_ca = collections.defaultdict(list); tick_of = collections.defaultdict(collections.Counter); cash = collections.Counter()
    for p in posts:
        evm, sol, ct = extract(p["text"]); ct |= set(p["cashtags"])
        for c in ct: cash[c] += 1
        for ca in evm | sol:
            by_ca[ca].append(p)
            for c in ct: tick_of[ca][c] += 1
    ticker_cas = collections.defaultdict(set)
    for ca, cnt in tick_of.items():
        if cnt: ticker_cas[cnt.most_common(1)[0][0]].add(ca)
    seen = seen_index(); mc = C.mdb(); k = gate_cfg(); import discovery as DS
    cands = []; RES = {}
    from concurrent.futures import ThreadPoolExecutor
    def _r(ca):
        try: RES[ca] = resolve(ca, None)
        except Exception as e: RES[ca] = None; print("resolve err", ca[:10], C.redact(e))
    with ThreadPoolExecutor(8) as ex: list(ex.map(_r, list(by_ca)))
    with C._CL:
        try: C.credit(mc, "rest", len(by_ca)); mc.commit()
        except Exception: pass
    for ca, group in by_ca.items():
        tk = tick_of[ca].most_common(1)[0][0] if tick_of[ca] else None
        b = buzz(group, {tk: ticker_cas.get(tk, set())} if tk else {})
        c = {"ca": ca, "ticker": tk, "chain_type": "evm" if ca.startswith("0x") else "solana", "buzz": b, "x_posts": [
            {"url": p["url"], "user": p["username"], "followers": p.get("followers"), "likes": p["pm"].get("like_count"), "rts": p["pm"].get("retweet_count"),
             "created_at": p["created_at"], "text": p["text"][:200]} for p in sorted(group, key=lambda p: -f(p["pm"].get("like_count")))[:6]]}
        prev = seen.get(A.norm(ca))
        try: pools = RES[ca]
        except Exception as e: c.update(stage="resolve-error", reason=C.redact(e)[:120]); cands.append(c); continue
        if pools is None: c.update(stage="resolve-error", reason="CoinGecko search failed"); cands.append(c); continue
        if not pools: c.update(stage="unresolved", reason="no pool on " + "/".join(nets())); cands.append(c); continue
        p = pools[0]; net, _, pool = p["id"].partition("_"); key = f"{net}_{pool}"
        why, m = DS.quick(p, k); c.update(network=net, pool=pool, key=key, symbol=(m["name"] or "").split(" / ")[0], metrics=m,
                                          gt=utm.pool_url(net, pool, "research-pool"), gt_token=utm.token_url(net, ca, "research-token"), other_pools=len(pools) - 1)
        prev = prev or seen.get(key)
        if prev and not (prev["verdict"] in ("discard", "deep:discard") and grown(prev["metrics"], m)):
            c.update(stage="already-assessed", reason=f"{prev['sect']} {prev['verdict']} @ {prev['at']} (no >=50% growth)"); cands.append(c); continue
        if prev: c["recheck"] = f"grown since {prev['at']}"
        if why: c.update(stage="gate-fail", reason="; ".join(why)); cands.append(c); continue
        c["stage"] = "gate-pass"; cands.append(c)
    for c in cands:   # rank: buzz quality first, then market activity
        m = c.get("metrics") or {}
        c["rank_score"] = round(c["buzz"]["score"] * 0.6 + min(40, f(m.get("buyers_h1")) / 5 + (f(m.get("liq")) ** 0.5) / 20), 1) if c.get("stage") == "gate-pass" else round(c["buzz"]["score"] * 0.3, 1)
    cands.sort(key=lambda c: (c.get("stage") != "gate-pass", -c["rank_score"]))
    queued = []
    def ok(c):   # buzz must be non-shill, OR broad (3+ authors), OR the market confirms it (many real-looking buyers on decent liq)
        if c.get("stage") != "gate-pass": return False
        m = c["metrics"]
        if f(m.get("buyers_h1")) >= k.get("market_confirm_buyers_h1", 300) and f(m.get("liq")) >= k.get("market_confirm_liq", 20000):
            c["buzz"]["flags"].append("market-confirmed (buyers/liq) despite buzz quality"); return True
        return c["buzz"]["grade"] != "shill/thin" or c["buzz"]["unique_authors"] >= 3
    passing = [c for c in cands if ok(c)]
    for c in cands:
        if c.get("stage") == "gate-pass" and c not in passing: c.update(stage="buzz-fail", reason=f"buzz {c['buzz']['score']} {c['buzz']['grade']}: " + ", ".join(c["buzz"]["flags"]))
    if deep:
        q = load_queue()
        for c in passing[:top]:
            key, net, pool, ca = c["key"], c["network"], c["pool"], c["ca"]
            with C._CL:
                mc.execute("insert or replace into discoveries(key,ca,network,pool,symbol,seen_at,stage,reason,buyers,liq) values(?,?,?,?,?,?,?,?,?,?)",
                           (key, ca if net == "solana" else ca.lower(), net, pool, c["symbol"], C.now_iso(), "deep", "x-first", c["metrics"]["buyers_h1"], c["metrics"]["liq"])); mc.commit()
            try: DS._deep(key, net, pool, ca, c["metrics"])
            except Exception as e: c.update(stage="deep-error", reason=C.redact(e)[:150]); continue
            path = f"{BASE}/research/{net}_{ca}.json"
            try: r = json.load(open(path))
            except Exception: c.update(stage="deep-error", reason="no research file"); continue
            xl = [[f"@{p['user']}: {p['text'][:60]}", p["url"]] for p in c["x_posts"]]
            r.update(source="x-first", buzz=c["buzz"], x_posts=c["x_posts"], x_links=xl, ticker=c["ticker"]); json.dump(r, open(path, "w"), indent=1)
            c.update(stage="deep:" + r["prelim_verdict"], deep_score=r["score"], fail_reasons=r["fail_reasons"], human=r["wallet_score"].get("human_participation"),
                     smart_money=r["smart_money_wallets"], payload_file=f"research/{net}_{ca}.json")
            if r["prelim_verdict"] == "discard":   # SCOUT (near-miss): soft-only discard + strong momentum; copycat w/o CA buzz is hard
                try:
                    import scout as SC
                    cop = any("copycat" in fl for fl in c["buzz"]["flags"])
                    ok_s, cav, hard = SC.classify(r, ca_buzz=c["buzz"]["posts"], namesakes=1 if cop else 0)
                    if ok_s and cop: cav.append("copycat ticker exists — CA-verified buzz only")
                    if ok_s and c["buzz"]["grade"] == "shill/thin": cav.append(f"thin/shill buzz ({c['buzz']['score']})")
                    if ok_s and not SC.seen(A.norm(ca, net)) and SC.allow(A.norm(ca, net), "forward")[0] and SC.live_liq_ok(ca, net)[0]:
                        r["prelim_verdict"] = "Scout?"; r["scout"] = {"caveats": cav, "fail_reasons": r["fail_reasons"]}; json.dump(r, open(path, "w"), indent=1)
                        SC.mark(A.norm(ca, net), "forward", "x-first"); c.update(stage="deep:Scout?", scout_caveats=cav)
                except Exception as e: c.update(scout_err=C.redact(e)[:120])
            if r["prelim_verdict"] != "discard" or c["buzz"]["grade"] == "organic":
                q = [x for x in q if x["ca"].lower() != ca.lower()]
                q.append({"ca": ca, "network": net, "pool": pool, "key": key, "symbol": r["token"].get("symbol"), "prelim_verdict": r["prelim_verdict"], "score": r["score"], "scout_caveats": (r.get("scout") or {}).get("caveats"),
                          "buzz_score": c["buzz"]["score"], "buzz_grade": c["buzz"]["grade"], "payload_file": c["payload_file"], "x_links": xl[:4], "source": "x-first",
                          "queued_at": C.now_iso(), "status": "pending"})
                queued.append(ca)
        save_queue(q)
    out = {"run_at": C.now_iso(), "secs": round(time.time() - t0, 1), "files": [os.path.basename(x) for x in files], "posts": len(posts), "cas": len(by_ca),
           "top_cashtags": cash.most_common(15), "counts": dict(collections.Counter((c.get("stage") or "?").split(":")[0] + (":" + c["stage"].split(":")[1] if c.get("stage", "").startswith("deep:") else "") for c in cands)),
           "queued": queued, "candidates": cands}
    os.makedirs(f"{XF}/runs/{ts}", exist_ok=True); json.dump(out, open(f"{XF}/runs/{ts}/candidates.json", "w"), indent=1); json.dump(out, open(f"{XF}/last_run.json", "w"), indent=1)
    for fp in files:
        if fp.startswith(XF + "/inbox/"): shutil.move(fp, f"{XF}/runs/{ts}/" + os.path.basename(fp))
    hist = C.kv_get(mc, "xfirst_runs", []); hist = (hist + [{k2: out[k2] for k2 in ("run_at", "posts", "cas", "counts", "queued")}])[-200:]; C.kv_set(mc, "xfirst_runs", hist); mc.commit()
    print(json.dumps({k2: out[k2] for k2 in ("run_at", "secs", "posts", "cas", "counts", "queued")}))
    for c in cands: print(f"  {c.get('stage','?'):<18} {c.get('network','-'):<9} {(c.get('symbol') or c.get('ticker') or '?')[:14]:<14} buzz {c['buzz']['score']:>5} {c['buzz']['grade']:<10} au {c['buzz']['unique_authors']} {c['ca'][:12]}  {c.get('reason','')[:90]}")
    return out
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "run":
        a = a[1:]; top = 3
        if "--top" in a: i = a.index("--top"); top = int(a[i + 1]); del a[i:i + 2]
        deep = "--no-deep" not in a; run([x for x in a if not x.startswith("--")], deep, top)
    elif a[0] == "done":
        q = load_queue(); n = 0
        for x in q:
            if A.same(x["ca"], a[1]) and x["status"] == "pending": x["status"] = "done"; x["done_at"] = C.now_iso(); n += 1
        save_queue(q); print("done", n)
    elif a[0] == "queue": print(json.dumps([x for x in load_queue() if x["status"] == "pending"], indent=1))
