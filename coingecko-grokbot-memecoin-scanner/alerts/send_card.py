#!/usr/bin/env python3
"""Send a signal alert: PNG chart card + caption (narrative, sizing line, links) + buttons (Buy rec / 0.5x / 2x / Skip).
Usage: send_card.py alert.json [--dry]   (alert.json schema: docs/ALERTS.md). Records alert, watchlist, outcome rows."""
import json, os, sys, time, html
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); sys.path.insert(0, _ROOT + "/alerts")
import common as C, sizing, card, core, requests, utm
def kb(ca, net, pool, sz):
    return {"inline_keyboard": [
        [{"text": f"🟢 Buy rec ${sz['rec']:,.0f}", "callback_data": f"b:{sz['rec']:g}:{ca}"}, {"text": f"Buy 0.5x ${sz['half']:,.0f}", "callback_data": f"b:{sz['half']:g}:{ca}"},
         {"text": f"Buy 2x ${sz['double']:,.0f}", "callback_data": f"b:{sz['double']:g}:{ca}"}],
        [{"text": "⏭ Skip", "callback_data": f"k:{ca}"}, {"text": "🔕 Mute", "callback_data": f"m:{ca}"}, {"text": "📊 Positions", "callback_data": "p"}],
        [{"text": "🦎 GeckoTerminal", "url": utm.pool_url(net, pool, "tg-alert-pool")}, {"text": "𝕏 CA search", "url": f"https://x.com/search?q={ca}&f=live"}]]}
def caption(a, sz):
    e = core.esc; m = a.get("metrics") or {}; tag = a.get("tag", "Watch")
    icon = "🔥" if tag.lower().startswith("organic") else "🔭" if tag.lower().startswith("scout") else "👀"
    src = a.get("source") or "cg-first"
    src_badge = "𝕏→CG" if str(src).startswith("x") else "CG→𝕏"
    xs = "".join(f'\n• <a href="{e(u)}">{e(t)[:40]}</a>' for t, u in (a.get("x_links") or [])[:4])
    head = f"{icon} <b>SCOUT · near-miss</b>" if tag.lower().startswith("scout") else f"{icon} <b>{e(tag.upper())}</b> ({e(a.get('confidence','low'))})"
    cav = a.get("caveats") or []
    cavl = (f"\n⚠️ <b>Why it missed:</b> {e('; '.join(cav))}") if tag.lower().startswith("scout") else ""
    pool_href = utm.html_href(utm.pool_url(a["network"], a.get("pool") or "", "tg-alert-pool"))
    token_href = utm.html_href(utm.token_url(a["network"], a["ca"], "tg-alert-token"))
    s = (f"{head} · <b>{e(a.get('symbol'))}</b> on {e(a['network'])} · score <b>{a.get('score','-')}</b> · <i>{src_badge}</i>\n"
         f"liq ${m.get('liq',0):,.0f} · FDV ${m.get('fdv',0):,.0f} · age {m.get('age_min','?')}m · human {a.get('human_score','-')}{cavl}\n\n"
         f"📖 {e(a.get('narrative') or 'Narrative pending.')}\n{xs}\n\n💵 {e(sz['line'])}\n<code>{a['ca']}</code>\n"
         f'<a href="{pool_href}">Pool</a> · <a href="{token_href}">Token</a>')
    attr = utm.html_href(utm.tag("https://www.coingecko.com/en/api", "tg-card-attribution", source="grokbot"))
    s += f'\nData provided by <a href="{attr}">CoinGecko</a>'
    return s
def send(a, dry=False):
    sys.path.insert(0, _ROOT + "/lib"); import addr as A; ca = A.norm(a["ca"], a.get("network")); net, pool = a["network"], a["pool"]
    if core.is_muted(ca): print("muted"); return None
    if str(a.get("tag", "")).lower().startswith("scout"):   # Scout gates: dedupe per CA, ~3/h, never old/re-alerted, live liq >= $8k now
        import scout as S
        if not a.get("caveats"): print("scout refused: caveats line required"); return None
        if (a.get("ca_buzz_authors") or 0) < 1: print("scout refused: needs >=1 non-shill X author posting the exact CA (ca_buzz_authors); ticker-only buzz doesn't count"); return None
        if S.seen(ca) and not dry: print("scout refused: already alerted"); return None
        ok, why = S.allow(ca, "card")
        if not ok and not dry: print("scout refused:", why); return None
        lok, l = S.live_liq_ok(ca, net)
        if not lok: print(f"scout refused: live liquidity ${l:,.0f} < ${S.cfg()['min_live_liq']:,}"); return None
        a.setdefault("metrics", {})["liq"] = l
    sz = sizing.recommend(net, pool, a.get("tag", "Watch"), a.get("confidence", "low"), a.get("score"), a.get("human_score"),
                          len(a.get("bundles") or []), a.get("bot_share", 0), (a.get("metrics") or {}).get("liq"))
    png = card.render(a, f"{C.BASE}/cards/{ca[:10]}_{int(time.time())}.png"); cap = caption(a, sz); k = kb(ca, net, pool, sz)
    if dry: print(json.dumps({"png": png, "caption_len": len(cap), "caption": cap, "kb": k}, indent=1)); return png
    own = core.owner(); short = cap if len(cap) <= 1024 else cap[:1000].rsplit("\n", 1)[0] + "\n…(story continues below)"
    r = requests.post(f"https://api.telegram.org/bot{core._tok()}/sendPhoto", data={"chat_id": own["chat_id"], "caption": short, "parse_mode": "HTML", "reply_markup": json.dumps(k)},
                      files={"photo": open(png, "rb")}, timeout=60).json()
    if not r.get("ok"): print("send failed", C.redact(r.get("description"))); return None
    mid = r["result"]["message_id"]
    if len(cap) > 1024: core.send(own["chat_id"], cap, reply_to=mid)
    c = C.pinit(core.db()); t = C.now_iso()
    c.execute("insert or replace into alerts values(?,?,?,?,?,?,?,?,?,?,?)", (mid, own["chat_id"], ca, net, pool, a.get("symbol"), a.get("tag"), a.get("confidence"), a.get("human_score"), cap, t))
    c.execute("insert or replace into watchlist values(?,?,?,?,?,?,?)", (ca, net, pool, a.get("symbol"), a.get("tag"), t, time.time() + 24 * 3600))
    px = C.last_price(C.mdb(), ca, 1e9)
    c.execute("insert or ignore into outcomes(ca,network,pool,symbol,alerted_at,alert_px,tag,confidence,score,decision) values(?,?,?,?,?,?,?,?,?,?)",
              (ca, net, pool, a.get("symbol"), t, a.get("price") or (px[0] if px else None), a.get("tag"), a.get("confidence"), a.get("score"), "pending"))
    c.execute("insert into decisions(ts,ca,network,pool,action,usd,rec_usd,tag,confidence,score,source) values(?,?,?,?,?,?,?,?,?,?,?)", (t, ca, net, pool, "alerted", None, sz["rec"], a.get("tag"), a.get("confidence"), a.get("score"), "send_card"))
    c.commit()
    if str(a.get("tag", "")).lower().startswith("scout"):
        import scout as S; S.mark(ca, "card", a.get("source") or "")
    print("sent", mid); return mid
if __name__ == "__main__":
    send(json.load(open(sys.argv[1])), dry="--dry" in sys.argv)
