#!/usr/bin/env python3
"""Discovery on `discovery.interval_s` (default 60s): new pools on each enabled network, plus Megafilter when the
plan includes it (otherwise trending pools and the same local filters). Deep research then reads token info, pool
trades and, on the analyst tier and above, top holders, top traders, the holder chart and wallet profiles. Missing paid
data is recorded as not available and is not a fail. The payload is queued for the scanner routine.
DISCOVERY_DRY=1 -> no POST (payload still written to research/)."""
import json, os, subprocess, sys, time, threading, urllib.request, datetime as D
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import common as C, addr as A, utm
log = C.logger("discovery"); DRY = os.environ.get("DISCOVERY_DRY") == "1"; mc = C.mdb(); lock = C._CL; busy = set()
mc.execute("create table if not exists discoveries(key text primary key, ca text, network text, pool text, symbol text, seen_at text, stage text, reason text, score real, payload text)"); mc.commit()
for col in ("buyers real", "liq real"):
    try: mc.execute(f"alter table discoveries add column {col}"); mc.commit()
    except Exception: pass
FWD_CAP_H = 12   # research forwards per hour
RECHECK_GROWTH = 1.5   # discarded tokens are only re-researched when buyers_h1 or liquidity grew >= 50%
SKIP_HOLDERS = ("pool manager", "pool", "dead", "burn", "router", "vault", "locker")
def seen_keys():
    st = C.BASE + "/state.json"
    try: s = json.load(open(st)); ks = set((s.get("assessed") or {}).keys()) | set((s.get("pending") or {}).keys())
    except Exception: ks = set()
    return ks | {r[0] for r in mc.execute("select key from discoveries")}
def f(x, d=0.0):
    try: return float(x)
    except Exception: return d
def quick(p, k):
    a = p["attributes"]; age_h = (time.time() - D.datetime.fromisoformat(a["pool_created_at"].replace("Z", "+00:00")).timestamp()) / 3600
    liq, fdv = f(a.get("reserve_in_usd")), f(a.get("fdv_usd")); h1 = a["transactions"]["h1"]; pc = f((a.get("price_change_percentage") or {}).get("h1"))
    why = []
    if liq < k["min_reserve_usd"]: why.append(f"liq {liq:.0f}")
    if not (k["min_fdv_usd"] <= fdv <= k["max_fdv_usd"]): why.append(f"fdv {fdv:.0f}")
    if age_h > k["max_age_hours"]: why.append(f"age {age_h:.1f}h")
    if (h1.get("buyers") or 0) < k["min_buyers_h1"]: why.append(f"buyers {h1.get('buyers')}")
    if not (k["min_h1_change_pct"] <= pc <= k["max_h1_change_pct"]): why.append(f"h1 {pc:.0f}%")
    if h1.get("sells", 0) == 0 and h1.get("buys", 0) > 20: why.append("no sells (honeypot?)")
    metrics = {"liq": liq, "fdv": fdv, "age_min": round(age_h * 60), "h1_change": pc, "buyers_h1": h1.get("buyers"), "sellers_h1": h1.get("sellers"),
                 "buys_h1": h1.get("buys"), "sells_h1": h1.get("sells"), "vol_h1": f((a.get("volume_usd") or {}).get("h1")), "m5_change": f((a.get("price_change_percentage") or {}).get("m5")),
                 "pool_created_at": a["pool_created_at"], "name": a.get("name"), "price": f(a.get("base_token_price_usd"))}
    try:
        import liquidity as LQ
        metrics["dex"] = LQ.dex_from_pool(p)
    except Exception:
        metrics["dex"] = ""
    return why, metrics
def ts(s): return D.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
def _unavail():
    import cgtier
    return cgtier.unavailable()
def _wallet_gap(score, hp, k):
    """True when skipped wallet or top-trader data sits next to a score boundary."""
    if C.cg_has("top_traders") and C.cg_has("wallets"): return False
    boundary = float(k.get("deep_min_human", 60) or 60)
    near_human = hp is not None and abs(hp - boundary) <= 8
    return abs((score or 0) - 70) <= 8 or near_human
def deep(key, net, pool, ca, m):
    try: _deep(key, net, pool, ca, m)
    except Exception as e:
        log('deep err', ca[:10], C.redact(e))
        with lock: mc.execute("update discoveries set stage='deep-error', reason=? where key=?", (C.redact(e)[:200], key)); mc.commit()
    finally: busy.discard(key)
def _deep(key, net, pool, ca, m):
    k = C.risk_cfg()["discovery"]; t0 = time.time(); out = {"type": "research", "ca": ca, "network": net, "pool": pool, "metrics": m}
    out["data_tier"] = C.tier()
    info = (C.cg(f"/networks/{net}/tokens/{ca}/info", None, mc) or {}).get("data", {}).get("attributes", {})
    out["token"] = {x: info.get(x) for x in ("name", "symbol", "gt_score", "gt_score_details", "is_honeypot", "is_nsfw", "developer_address", "developer_holding_percentage", "twitter_handle", "telegram_handle", "websites", "description", "categories", "holders")}
    holders_real = C.cg_has("top_holders")
    if holders_real:
        th = ((C.cg(f"/networks/{net}/tokens/{ca}/top_holders", None, mc) or {}).get("data") or {}).get("attributes", {}).get("holders") or []
        real = [h for h in th if not any(s in (h.get("label") or "").lower() for s in SKIP_HOLDERS) and not h["address"].lower().startswith("0x000000000000000000000000000000000000") and not h["address"].startswith("11111111111111111111")]
        top10 = sum(f(h["percentage"]) for h in real[:10]); out["holders"] = {"top10_pct_ex_pools": round(top10, 2), "top": [{"a": h["address"], "pct": f(h["percentage"]), "label": h.get("label")} for h in real[:15]]}
    else:
        th, real = [], []
        raw = (((info.get("holders") or {}).get("distribution_percentage") or {}).get("top_10"))
        top10 = f(raw) if raw not in (None, "") else None
        out["holders"] = {"top10_pct_approx": None if top10 is None else round(top10, 2),
                          "note": _unavail() if top10 is None else "approximate, from token info; includes pools and exchanges"}
    if C.cg_has("top_traders"):
        try: tt = ((C.cg(f"/networks/{net}/tokens/{ca}/top_traders", None, mc, timeout=30) or {}).get("data") or {}).get("attributes", {}).get("traders") or []
        except Exception: tt = []
        out["top_traders"] = [{"a": x.get("address"), "realized": x.get("realized_pnl_usd"), "unrealized": x.get("unrealized_pnl_usd"), "buy_usd": x.get("total_buy_usd"), "sell_usd": x.get("total_sell_usd")} for x in tt[:15]]
    else:
        tt = []; out["top_traders"] = []; out["top_traders_note"] = _unavail()
    tr = (C.cg(f"/networks/{net}/pools/{pool}/trades", None, mc) or {}).get("data") or []
    import trades as TR
    ws, skipped_anom = TR.accumulate(tr[::-1], net, A.norm)
    out["anomalous_trades_skipped"] = skipped_anom
    for h in real[:15]: ws.setdefault(A.norm(h["address"], net), {"address": A.norm(h["address"], net), "buy": 0, "sell": 0})["holding_pct"] = f(h["percentage"])
    wl = [dict(v, bought=(v["buy"] > 0 or "holding_pct" not in v) if True else None) for v in ws.values()]
    for v in wl:
        if v.get("holding_pct") and v["buy"] == 0 and v["sell"] == 0: v["bought"] = None
    if C.cg_has("holders_chart"):
        hc = ((C.cg(f"/networks/{net}/tokens/{ca}/holders_chart", {"days": 7}, mc) or {}).get("data") or {}).get("attributes", {}).get("token_holders_list") or []
    else:
        hc = []; out["holders_chart_note"] = _unavail()
    out["holders_chart"] = hc[-12:]
    if not C.cg_has("top_traders") or not C.cg_has("wallets"):
        try:
            import plan_tips; plan_tips.note_wallet_skip()
        except Exception: pass
    if net == "solana" and C.cg_has("wallets"):   # no balances/transfers on Solana: rebuild wallet history from PnL + wallet trades (cached 6h)
        try:
            import sol_profile
            prof_n = int(k.get("solana_profile_wallets", 10))
            tops = [A.norm(x.get("address"), net) for x in tt[:prof_n] if x.get("address")]
            early = [w for w, v in sorted(ws.items(), key=lambda kv: -(kv[1].get("buy") or 0))[:5]]
            out["solana_profiles"] = {a: {kk: v.get(kk) for kk in ("total_tokens", "realized_pnl", "win_rate", "closed_trades", "median_hold_s", "flags")}
                                      for a, v in sol_profile.profile_many(list(dict.fromkeys(tops + early)), mc, max_n=prof_n + 5).items() if isinstance(v, dict)}
        except Exception as e: log("sol profile err", C.redact(e))
    elif net == "solana":
        out["solana_profiles_note"] = _unavail()
    r = subprocess.run([sys.executable, C.BASE + "/walletdb.py", "score-token"], input=json.dumps({"token": ca, "chain": net, "wallets": wl}), capture_output=True, text=True, timeout=60)
    try: sc = json.loads(r.stdout)
    except Exception: sc = {"human_participation": None, "mix": {}, "bundles": [], "read": "score error"}
    sc.pop("detail", None)
    import human_pattern as HP
    pattern = HP.from_pool(net, pool, m.get("liq"), (C.risk_cfg().get("human_score") or {}), mc, trades=tr)
    wallets_on_data = C.cg_has("wallets") and C.cg_has("top_traders")
    hp, hsrc = HP.choose(sc, pattern, wallets_on_data)
    sc["wallet_human"] = sc.get("human_participation")
    sc["human_participation"] = hp
    sc["human_source"] = hsrc
    sc["trade_pattern"] = {k: pattern.get(k) for k in ("human_participation", "source", "n", "reasons")}
    out["wallet_score"] = sc
    out["human_score_source"] = hsrc
    smart = [a for a, d in json.loads(subprocess.run([sys.executable, C.BASE + "/walletdb.py", "lookup", *list(ws)[:200]], capture_output=True, text=True, timeout=60).stdout or "{}").items() if d and d.get("label") == "smart_money"]
    out["smart_money_wallets"] = smart
    flow = sum(v["buy"] for v in wl) / max(1, sum(v["buy"] + v["sell"] for v in wl))
    nb = len(sc.get("bundles") or []); top_b = any(set(b["members"]) & {A.norm(h["address"], net) for h in real[:10]} for b in sc.get("bundles") or [])
    hpot = info.get("is_honeypot"); hpot = True if hpot is True else (None if hpot in (None, "unknown") else False); dev = f(info.get("developer_holding_percentage"))
    top10_n = 0 if top10 is None else top10
    comp = {"human": hp, "safety": max(0, 100 - (40 if hpot is None else 100 if hpot else 0) * 0.5 - max(0, top10_n - 30) - max(0, dev - 5) * 2),
            "momentum": min(100, 40 + m["h1_change"] / 10 + (flow - 0.5) * 80 + min(30, (m["buyers_h1"] or 0) / 5)), "smart_money": min(100, 35 * len(smart)),
            "holder_growth": min(100, 50 + ((hc[-1][1] - hc[0][1]) / max(hc[0][1], 1) * 50 if len(hc) >= 2 else 0))}
    comp = {a: (None if b is None else round(max(0, b), 1)) for a, b in comp.items()}
    W = {"human": 0.35, "safety": 0.25, "momentum": 0.2, "smart_money": 0.1, "holder_growth": 0.1}
    db_has_smart = _db_has_smart()
    if not smart and not db_has_smart: W.pop("smart_money")      # no smart-money wallets in DB yet -> component has no data
    if len(hc) < 2: W.pop("holder_growth")                        # no holder history yet
    if hp is None: W.pop("human")                                 # unknown is not a placeholder 60; the other weights are renormalized
    score, out["score_weights"] = HP.weighted(comp, W)
    score = 0 if score is None else score
    try:
        import artificial as ART
        art = ART.assess(net, pool, m.get("age_min"), m.get("liq"), tr, mc, C.risk_cfg().get("artificial_chart") or {})
    except Exception as e:
        log("chart check", C.redact(e)); art = {"score": None, "band": "unknown", "reasons": [], "penalty": 0}
    out["artificial_chart"] = art
    if art.get("band") == "borderline" and art.get("penalty"):
        score = round(max(0, score - float(art["penalty"])), 1)
    fails = []
    if hpot: fails.append("honeypot")
    mix = sc.get("mix") or {}; nw = max(1, sum(mix.values())); unk = mix.get("unknown", 0) / nw
    wallets_on = C.cg_has("wallets")
    unverified = (unk >= 0.7) if wallets_on else False   # unknown wallet labels are a gap only when wallet lookups exist
    if hp is not None and hp < k["deep_min_human"] and not unverified: fails.append(f"human {hp}")
    if art.get("band") == "clear": fails.append("artificial chart: " + "; ".join(art.get("reasons") or ["engineered price action"]))
    if unverified and (score < 60 or (m["buyers_h1"] or 0) < 15): fails.append(f"unverified wallets, score {score}")
    if top_b: fails.append("bundle in top10")
    if holders_real and top10 > 65: fails.append(f"top10 {top10:.0f}%")
    elif (not holders_real) and top10 is not None and top10 > 75: fails.append(f"top10 approx {top10:.0f}%")
    if dev > 20: fails.append(f"dev {dev:.0f}%")
    if sc.get("read") in ("bot/bundle dominated", "insider heavy"): fails.append(sc["read"])
    import liquidity as LQ
    nr = LQ.nsfw_reason(info) if LQ.nsfw_discard() else ""
    if nr: fails.append(nr)
    lev = LQ.research_events(net, pool, (m or {}).get("dex") or "", info.get("developer_address"), m.get("liq"), mc)
    out["liquidity_events"] = {"skipped": lev.get("skipped"), "called": bool(lev.get("called")), "reason": lev.get("reason") or ""}
    if lev.get("reason"): fails.append(lev["reason"])
    bits = [x for x in (lev.get("reason"), nr) if x]
    if bits: out["reason_line"] = "; ".join(bits)
    if fails: prelim = "discard"
    elif unverified: prelim = "Watch? (wallets unverified)"
    elif score >= 70 and (smart or not wallets_on): prelim = "Organic Hype?"
    else: prelim = "Watch"
    if _wallet_gap(score, hp, k):
        out["plan_tip"] = "wallet_gap"
        try:
            import plan_tips; plan_tips.notify("wallet_gap")
        except Exception as e: log("plan tip", C.redact(e))
    out.update(prelim_verdict=prelim, fail_reasons=fails, score=score, flow_buy_share=round(flow, 2))
    if prelim == "discard":   # SCOUT (near-miss): soft-only discard with strong momentum; hard reasons never qualify
        try:
            import scout as SC
            ok_s, cav, hard = SC.classify(out)
            if ok_s: prelim = "Scout?"; out["scout"] = {"caveats": cav, "fail_reasons": fails}
        except Exception as e: log("scout err", C.redact(e))
    TALLY.append((time.time(), prelim))
    comp_store = {a: b for a, b in comp.items() if b is not None}
    out.update(components=comp_store, score=score, flow_buy_share=round(flow, 2), prelim_verdict=prelim, fail_reasons=fails, bundles_n=nb,
               links={"gt": utm.pool_url(net, pool, "research-pool"), "gt_token": utm.token_url(net, ca, "research-token"), "x_ca": f"https://x.com/search?q={ca}&f=live",
                      "x_ticker": f"https://x.com/search?q=%24{(info.get('symbol') or '')}&f=live"},
               research_secs=round(time.time() - t0, 1), generated_at=C.now_iso(), card_cmd=f"python3 {C.BASE}/alerts/send_card.py <alert.json>")
    path = f"{C.BASE}/research/{net}_{ca}.json"; json.dump(out, open(path, "w"), indent=1)
    with lock:
        mc.execute("update discoveries set stage=?, reason=?, score=?, payload=?, symbol=?, buyers=?, liq=? where key=?", ("deep:" + prelim, "; ".join(fails), score, path, info.get("symbol"), m["buyers_h1"], m["liq"], key)); mc.commit()
    log("deep", info.get("symbol"), net, prelim, score, fails, f"{out['research_secs']}s")
    if (out.get("artificial_chart") or {}).get("band") == "clear" and prelim == "discard":
        notify_chart(out)
    if prelim == "Scout?": forward_scout(out)
    elif prelim != "discard": forward(out)
    busy.discard(key)
TALLY = []
def tally_line():
    TALLY[:] = [x for x in TALLY if time.time() - x[0] < 3600]; v = [p.lower() for _, p in TALLY]
    o = sum(x.startswith("organic") for x in v); w = sum(x.startswith("watch") for x in v); s = sum(x.startswith("scout") for x in v)
    return f"{o} Organic Hype / {w} Watch / {s} Scout / {len(v) - o - w - s} Discard (last 1h)"
def notify_chart(out):
    """One Telegram line for a clear artificial-chart Discard. Deduped per CA."""
    art = out.get("artificial_chart") or {}
    reasons = "; ".join(art.get("reasons") or ["engineered price action"])
    sym = (out.get("token") or {}).get("symbol") or "?"
    text = f"Discard · {sym} on {out.get('network')}\nArtificial chart: {reasons}"
    key = "art_notice:" + str(out.get("network") or "") + ":" + str(out.get("ca") or "")
    try:
        if C.kv_get(mc, key): return
        C.kv_set(mc, key, {"at": C.now_iso(), "text": reasons[:300]})
        mc.commit()
    except Exception: pass
    try:
        import core
        own = core.owner()
        if own and os.environ.get("TELEGRAM_BOT_TOKEN"):
            core.send(own["chat_id"], core.esc(text))
    except Exception as e:
        log("chart note", C.redact(e))
def forward_scout(out):
    import scout as SC
    ca = A.norm(out["ca"], out["network"])
    if SC.seen(ca): log("scout skip (already alerted)", ca[:10]); return
    ok, why = SC.allow(ca, "forward")
    if not ok: log("scout skip", why, ca[:10]); return
    age = (out.get("metrics") or {}).get("age_min") or 0; need = SC.cfg().get("min_pool_age_min", 10)
    if age < need and not out.get("_scout_deferred"):   # fragile-pool rule: re-check when the pool is >= 10 min old
        out["_scout_deferred"] = True; threading.Timer((need - age) * 60 + 5, forward_scout, args=(out,)).start()
        log(f"scout deferred {need - age:.0f}m (pool {age}m old)", ca[:10]); return
    lok, l = SC.live_liq_ok(ca, out["network"])
    if not lok: log(f"scout skip live liq ${l:,.0f}", ca[:10]); return
    SC.mark(ca, "forward", "discovery"); log("SCOUT", out["token"].get("symbol"), out["network"], out["score"], "; ".join(out["scout"]["caveats"]))
    forward(out)
_SM = [0, None]
def _db_has_smart():
    if time.time() - _SM[0] > 300:
        try:
            import sqlite3; w = sqlite3.connect(C.BASE + "/wallets.db", timeout=10)
            _SM[1] = w.execute("select count(*) from wallets where label='smart_money'").fetchone()[0] > 0; w.close()
        except Exception: _SM[1] = False
        _SM[0] = time.time()
    return _SM[1]
def grown(row, m):
    """row = (buyers, liq) stored at discard time; True if buyers or liquidity grew >= 50% since."""
    b0, l0 = row
    return bool((b0 and (m["buyers_h1"] or 0) >= RECHECK_GROWTH * b0) or (l0 and m["liq"] >= RECHECK_GROWTH * l0))
FWD = []
import fwdq
def research_body(payload):
    body = dict(payload)
    if payload.get("prelim_verdict") == "Scout?":
        body["text"] = (f"[research] SCOUT (near-miss) candidate {payload['token'].get('symbol')} on {payload['network']} score {payload['score']}. "
                        f"Caveats: {'; '.join(payload['scout']['caveats'])}. Verify X buzz for the CA (0 CA buzz + live namesakes = copycat -> discard), write narrative, "
                        f"then send card with tag 'Scout' and a 'caveats' list via alerts/send_card.py (it enforces 3/h + dedupe). Payload file: research/{payload['network']}_{payload['ca']}.json")
        body["chat_id"] = None; body["source"] = "discovery"; return body
    extra = f" Reason: {payload['reason_line']}." if payload.get("reason_line") else ""
    body["text"] = (f"[research] {payload['prelim_verdict']} candidate {payload['token'].get('symbol')} on {payload['network']} score {payload['score']}. "
                                           f"Check X buzz + write narrative, then send card via alerts/send_card.py.{extra} Payload file: research/{payload['network']}_{payload['ca']}.json")
    body["chat_id"] = None; body["source"] = "discovery"; return body
def forward(payload):
    FWD[:] = [t for t in FWD if time.time() - t < 3600]
    if len(FWD) >= FWD_CAP_H: log("forward rate-limited", payload["ca"][:10]); return
    if not fwdq.research_enabled(): log("research forward OFF (risk.json discovery.research_forward)", payload["ca"][:10]); return
    if DRY: log("DRY forward", payload["ca"]); return
    body = research_body(payload)
    dedupe = f"research:{A.norm(payload['ca'], payload['network'])}:{payload['pool']}"
    if not os.environ.get("TELEGRAM_FORWARD_URL"):   # no webhook: queue locally; the scheduled CoinGecko-first routine reads pending_research.json
        q = fwdq.enqueue("research", body, dedupe, "queued-local (no webhook)")
        log("queued for scheduled scan" if q else "already queued", payload["ca"][:10]); return
    if fwdq.forwarding_paused():
        fwdq.enqueue("research", body, dedupe, "automation disabled; forward paused"); return
    ok, st, eb = fwdq.post(body)
    if ok: FWD.append(time.time()); log("forwarded research", payload["ca"][:10], st); return
    if fwdq.note_automation_disabled(st, eb, log=log):
        fwdq.enqueue("research", body, dedupe, "automation disabled"); return
    log("forward failed", st, C.redact(eb)); q = fwdq.enqueue("research", body, dedupe, f"{st} {eb}")
    log("fwdq queued" if q else "fwdq already queued", payload["ca"][:10])
_LD = [0]
def drain_queue():
    if time.time() - _LD[0] < 30: return
    _LD[0] = time.time()
    if not fwdq.research_enabled(): return
    try: fwdq.drain(lambda *a: log(*a), on_sent=lambda r: FWD.append(time.time()), kind="research")
    except Exception as e: log("fwdq drain err", C.redact(e))
_MF_LOGGED = [False]
def cycle():
    k = C.risk_cfg()["discovery"]; seen = seen_keys(); pools = []
    for n in k["networks"]:
        pools += (C.cg(f"/networks/{n}/new_pools", {"page": 1}, mc) or {}).get("data") or []
        if not C.cg_has("megafilter"):
            pools += (C.cg(f"/networks/{n}/trending_pools", {"page": 1}, mc) or {}).get("data") or []
    if C.cg_has("megafilter"):
        mf = C.cg("/pools/megafilter", {"networks": ",".join(k["networks"]), "sort": "pool_created_at_desc", "pool_created_hour_max": k["max_age_hours"],
                  "reserve_in_usd_min": k["min_reserve_usd"], "fdv_usd_max": k["max_fdv_usd"], "price_change_percentage_min": k["min_h1_change_pct"],
                  "price_change_percentage_max": k["max_h1_change_pct"], "price_change_percentage_duration": "1h", "buys_min": k["min_buyers_h1"], "buys_duration": "1h",
                  "buy_tax_percentage_max": k["max_tax_pct"], "sell_tax_percentage_max": k["max_tax_pct"], "include_unknown_honeypot_tokens": "true", "checks": "no_honeypot"}, mc)
        pools += (mf or {}).get("data") or []
    elif not _MF_LOGGED[0]:
        _MF_LOGGED[0] = True
        import cgtier
        log("Megafilter needs", cgtier.needs_plan("analyst") + ", so discovery is using new and trending pools with the local filters.")
    dedup, seen_ids = [], set()
    for p in pools:
        pid = (p or {}).get("id")
        if not pid or pid in seen_ids: continue
        seen_ids.add(pid); dedup.append(p)
    pools = dedup; new = 0
    disc = {r[0]: (r[1], r[2], r[3]) for r in mc.execute("select key, ca, buyers, liq from discoveries where stage='deep:discard'")}
    disc_ca = {v[0]: (k, v[1], v[2]) for k, v in disc.items()}
    for p in pools:
        key = p["id"]
        ca0 = A.norm(p["relationships"]["base_token"]["data"]["id"].partition("_")[2], key.partition("_")[0])
        prev = disc.get(key) and (key, disc[key][1], disc[key][2]) or (disc_ca.get(ca0) if key not in seen else None)
        if prev:   # previously deep-discarded (this pool or same CA): recheck only on >=50% growth
            if key in busy or len(busy) >= 3: continue
            why, m = quick(p, k)
            if why or not grown(prev[1:], m): seen.add(key); continue
            log("recheck grown", ca0[:10], "buyers", prev[1], "->", m["buyers_h1"], "liq", prev[2], "->", round(m["liq"]))
            with lock:
                mc.execute("insert or replace into discoveries(key,ca,network,pool,symbol,seen_at,stage,reason,buyers,liq) values(?,?,?,?,?,?,?,?,?,?)",
                           (key, ca0, key.partition("_")[0], key.partition("_")[2], (m["name"] or "").split(" / ")[0], C.now_iso(), "deep", "recheck grown", m["buyers_h1"], m["liq"])); mc.commit()
            busy.add(key); seen.add(key); threading.Thread(target=deep, args=(key, key.partition("_")[0], key.partition("_")[2], ca0, m), daemon=True).start(); continue
        if key in seen: continue
        if len(busy) >= 3: continue   # retry next cycle
        seen.add(key); net, _, pool = key.partition("_"); ca = A.norm(p["relationships"]["base_token"]["data"]["id"].partition("_")[2], net)
        why, m = quick(p, k); new += 1
        with lock:
            mc.execute("insert or ignore into discoveries(key,ca,network,pool,symbol,seen_at,stage,reason) values(?,?,?,?,?,?,?,?)", (key, ca, net, pool, (m["name"] or "").split(" / ")[0], C.now_iso(), "quick-fail" if why else "deep", "; ".join(why)))
            mc.execute("update discoveries set buyers=?, liq=? where key=?", (m["buyers_h1"], m["liq"], key)); mc.commit()
        # young pools that fail only on buyers/fdv get re-checked: forget them after 3 min
        if why and all(w.split()[0] in ("buyers", "fdv", "liq") for w in why) and m["age_min"] < 30:
            with lock: mc.execute("update discoveries set stage='recheck' where key=?", (key,)); mc.commit()
        if not why: busy.add(key); threading.Thread(target=deep, args=(key, net, pool, ca, m), daemon=True).start()
    with lock:
        mc.execute("delete from discoveries where stage='recheck' and seen_at < ?", ((D.datetime.now(C.MYT) - D.timedelta(minutes=3)).isoformat(timespec="seconds"),)); mc.commit()
    return len(pools), new
def main():
    C.start_heartbeat(log)
    log("start", "DRY" if DRY else "RUN (paper)"); beat = 0
    while True:
        t = time.time()
        drain_queue()
        try:
            import usage
            usage.refresh()
        except Exception as e: log("usage", C.redact(e))
        try: n, new = cycle()
        except Exception as e: log("cycle err", C.redact(e)); n = new = -1
        if time.time() - beat > 60: log("heartbeat pools", n, "new", new, "busy", len(busy)); log("tally", tally_line()); beat = time.time()
        remain = max(2, C.risk_cfg()["discovery"]["interval_s"] - (time.time() - t))
        while remain > 0:
            step = min(60, remain); time.sleep(step); remain -= step
            if remain > 0: log("heartbeat", "interval wait")
if __name__ == "__main__": main()
