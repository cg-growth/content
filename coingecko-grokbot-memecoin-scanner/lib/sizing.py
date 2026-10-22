"""Dynamic paper position sizing: rec = min(pool cap, conviction-scaled, portfolio cap). Recomputed at send time."""
import statistics, sys, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import common as C
def recommend(net, pool, tag="Watch", confidence="low", score=None, human=None, bundles=0, bot_share=0.0, liq=None, mc=None):
    if str(tag).lower().startswith("scout"):   # near-miss: Watch/low sizing scaled down (risk.json scout.size_mult, ~0.3-0.5x)
        import scout as _S; mult = _S.cfg()["size_mult"]; s0 = C.risk_cfg()["sizing"]
        r = recommend(net, pool, "Watch", "low", score, human, bundles, bot_share, liq, mc)
        rec = r["rec"] and max(s0["min_usd"], round(r["rec"] * mult)); rec = round(rec / 5) * 5 if rec >= 10 else rec
        r.update(rec=rec, half=max(s0["min_usd"], round(rec / 2)), double=rec * 2,
                 line=f"Scout size ${rec:,.0f} = {mult:g}x Watch (${r['rec']:,.0f}) — near-miss, small. " + r["line"].split(": ", 1)[-1])
        return r
    import core
    k = C.risk_cfg(); s = k["sizing"]; mc = mc or C.mdb(); pc = core.db()
    cash = core.cash(pc); npos = pc.execute("select count(*) from positions").fetchone()[0]
    eq = cash + sum(r["cost_usd"] for r in pc.execute("select cost_usd from positions")); pc.close()
    # pool cap: median recent trade size, <= pool_liq_pct_cap of liquidity
    d = C.cg(f"/networks/{net}/pools/{pool}/trades", None, mc) or {}
    sz = [float(x["attributes"]["volume_in_usd"] or 0) for x in d.get("data", [])]; med = statistics.median(sz) if sz else 25.0
    if liq is None:
        pi = C.cg(f"/networks/{net}/pools/{pool}", None, mc) or {}; liq = float(((pi.get("data") or {}).get("attributes") or {}).get("reserve_in_usd") or 0)
    pool_cap = min(med * s["trade_size_multiple_of_median"], liq * s["pool_liq_pct_cap"] / 100) if liq else med
    shrink = 1.0; why = []
    ps = s["predatory_shrink"]
    if human is not None and human < ps["human_below"]: shrink *= 0.6; why.append(f"human {human:.0f}<{ps['human_below']}")
    if bundles: shrink *= ps["bundle_present"]; why.append("bundles")
    if bot_share and bot_share * 100 > ps["bot_share_above_pct"]: shrink *= 0.6; why.append(f"bots {bot_share*100:.0f}%")
    pool_cap *= shrink
    conv = s["conviction"].get(f"{tag}:{confidence}", 0.3) * (0.7 + 0.6 * ((score or 50) / 100))
    port = cash * s["portfolio_base_pct_of_cash"] / 100 * max(0.25, 1 - s["portfolio_decay_per_open_position"] * npos)
    port = min(port, eq * k["max_equity_pct_per_token"] / 100)
    conv_usd = port * conv * 2  # conviction-scaled from the portfolio base (1.0 conviction = 2x base)
    rec = min(pool_cap, conv_usd, port * 2)
    rec = max(s["min_usd"], min(s["max_usd"], rec))
    if npos >= k["max_open_positions"]: rec = 0; why.append("max open positions")
    rec = round(rec / 5) * 5 if rec >= 10 else round(rec)
    limiter = min((pool_cap, "pool"), (conv_usd, "conviction"), (port * 2, "portfolio"))[1]
    line = (f"Size ${rec:,.0f}: limited by {limiter} (median trade ${med:,.0f}, 1% liq ${liq*0.01:,.0f}, "
            f"conviction {tag}/{confidence}, {npos} open, cash ${cash:,.0f})" + (f"; shrunk: {', '.join(why)}" if why else ""))
    return {"rec": rec, "half": max(s["min_usd"], round(rec / 2)), "double": min(s["max_usd"] * 2, rec * 2), "line": line,
            "pool_cap": pool_cap, "conv_usd": conv_usd, "port_cap": port * 2, "median_trade": med, "liq": liq}
