"""Rule-based natural-language parser for the paper-trading bot (text + voice transcripts).
parse(text, reply_ca, c) -> dict:
  {"kind":"trade","side":"buy","ca":..,"usd":float}         buy needs confirmation
  {"kind":"trade","side":"sell","ca":..,"amt":"50%"|"all"|"25"}
  {"kind":"ambiguous","side":"buy","usd":..,"ticker":..,"hits":[...]}  multiple CAs share ticker
  {"kind":"query","cmd":"pnl"|"report"|"auto"|"autoreport"|"compare"|"portfolio"|"positions"|"balance"|"ledger"|"help"}
  {"kind":"error","msg":..}   understood intent but missing/ambiguous info
  None                        not understood -> forward / hint"""
import re, sys
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
sys.path.insert(0, _ROOT + "/lib"); import addr as A
WORDNUM = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,
  "twelve":12,"fifteen":15,"twenty":20,"twenty-five":25,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,
  "seventy-five":75,"eighty":80,"ninety":90,"hundred":100,"a hundred":100,"one hundred":100,"two hundred":200,
  "two hundred fifty":250,"two hundred and fifty":250,"three hundred":300,"five hundred":500,"a thousand":1000,
  "one thousand":1000,"a grand":1000,"one grand":1000}
FRAC = [(r"\b(half|halve|50/50)\b", "50%"), (r"\b(a |one )?quarter\b", "25%"), (r"\b(a |one )?third\b", "33.33%"),
        (r"\b(three quarters|three-quarters)\b", "75%"), (r"\btwo thirds\b", "66.67%")]
ALL = r"\b(all|everything|it all|the lot|entire|whole|full|max|100 ?%|every last|close|exit|out of|get out)\b"
BUY_V = r"\b(buy|bought|grab|ape|aping|apeing|get me|pick up|purchase|long|add|load up|throw|put|scoop|snag|get (?:me )?(?:into|in on|in)|go into|jump (?:into|in on|in)|enter|yolo)\b"
SELL_V = r"\b(clip|initials?|sell|dump|close|exit|take profits?|tp|trim|cut|unload|offload|get out|cash out|bail)\b"
STOP = set("""buy grab ape aping get me pick up purchase long add load throw put scoop snag sell dump close exit take profit profits tp
 trim cut unload offload cash out bail of in into on the a an my some more worth bucks buck dollars dollar usd usdc it its this that
 all everything half quarter third percent pct position bag bags please pls now just and for with lot entire whole full max me i
 want to would like let s go but yeah yes ok okay hey bot of from at off rest remaining back few tokens token coin""".split())
QUERIES = [("compare", r"\b(compare (the |our )?books?|human vs\.? ai|ai vs\.? (human|me)|who('?s| is) winning)\b"),
           ("autoreport", r"\b(ai (book )?report( card)?|your report card)\b"),
           ("auto", r"\b(how('?s| is) (your|the ai'?s?|ai) book( doing)?|your book|ai book|your (positions|trades|pnl))\b"),
           ("report", r"\b(report ?card|/?report|how did i do|how have i done|scorecard|score card|track record|my stats|win rate)\b"),
           ("pnl", r"\b(how am i doing|how('?s| is) (it|my portfolio|my account) (going|doing)|pnl|p ?& ?l|p and l|profit and loss|performance|am i (up|down)|how much (am i|have i) (up|down|made|lost))\b"),
           ("portfolio", r"\b(portfolio (chart|image|pic)|show (me )?(my )?portfolio|/?portfolio)\b"),
           ("positions", r"\b(positions?|holdings|my bags|what do i (hold|own|have)|open trades|show (me )?(my )?(bags|positions))\b"),
           ("balance", r"\b(balance|how much cash|cash left|buying power|equity)\b"),
           ("ledger", r"\b(ledger|trade history|recent trades|my trades|last trades)\b"),
           ("help", r"^(help|commands|what can you do)\b")]
def norm(t):
    t = (t or "").strip().lower().replace("’", "'")
    t = re.sub(r"[!?.,;]+(\s|$)", r" ", t)
    for w in sorted(WORDNUM, key=len, reverse=True):
        t = re.sub(rf"\b{w}\b", str(WORDNUM[w]), t)
    t = re.sub(r"(\d+) (\d+)\b", lambda m: str(int(m.group(1)) + int(m.group(2))) if int(m.group(1)) >= 20 and int(m.group(1)) % 10 == 0 and int(m.group(2)) < 10 else m.group(0), t)
    t = re.sub(r"(\d)\s*k\b", lambda m: m.group(1) + "000", t)
    t = re.sub(r"\bper ?cent\b", "%", t); t = re.sub(r"(\d)\s+%", r"\1%", t)
    return re.sub(r"\s+", " ", t).strip()
def _target(t, raw, c, core, reply_ca=None):
    """CA-first (EVM or Solana). Ticker never silently picks a namesake — ambiguous hits bubble up."""
    cas = A.find_cas(raw)
    if cas: return cas[0], None
    cands = re.findall(r"\$?[a-z][a-z0-9_\-]{1,19}", re.sub(r"\$\d[\d.,]*", " ", t))
    for w in cands:
        w2 = w.lstrip("$")
        if w2 in STOP and not w.startswith("$"): continue
        ca, net = core.resolve(w2, c, prefer_ca=reply_ca)
        if isinstance(net, dict) and net.get("ambiguous"):
            return None, {"ambiguous": net["ambiguous"], "ticker": net["ticker"], "word": w2}
        if ca: return ca, w2
        r = c.execute("select ca from positions where lower(symbol)=?", (w2,)).fetchone()
        if r: return r["ca"], w2
    unknown = [w.lstrip("$") for w in cands if w.lstrip("$") not in STOP]
    return None, (unknown[0] if unknown else None)
TYPO_BUY = r"^(but|buu|buyy|bui|bye|by|buyt)\b(?=\s*\$?\s?\d)"
def recent_alert(c, minutes=45):
    try:
        from datetime import datetime, timedelta, timezone
        import localtz; cut = (datetime.now(localtz.LOCAL_TZ) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
        r = c.execute("select ca from alerts where sent_at>=? order by sent_at desc limit 1", (cut,)).fetchone()
        return r["ca"] if r else None
    except Exception: return None
def parse(text, reply_ca=None, c=None, core=None):
    if core is None: import core
    raw = text or ""; t = norm(raw)
    if not t: return None
    if re.search(TYPO_BUY, t) and (reply_ca or recent_alert(c)): t = re.sub(TYPO_BUY, "buy", t)
    tq = re.sub(r"^(but|so|and|ok|okay|hey|yo)\s+", "", t)
    if re.match(r"^(why|what|whats|what's|how|is|are|was|were|should|could|would|do|does|did|can|who|when|where)\b", tq) or (raw.strip().endswith("?") and not re.match(r"^(buy|sell|ape|grab|dump|close|trim|take)\b", tq)):
        for cmd, rx in QUERIES:
            if re.search(rx, t): return {"kind": "query", "cmd": cmd}
        return None
    is_sell = re.search(SELL_V, t); is_buy = re.search(BUY_V, t)
    if not (is_sell or is_buy):
        for cmd, rx in QUERIES:
            if re.search(rx, t): return {"kind": "query", "cmd": cmd}
        return None
    if re.search(r"\b(clip|initials?)\b", t):
        mclip = re.search(r"(\d+(?:\.\d+)?)\s*%", t); spec = "initial" if re.search(r"\binitials?\b", t) else (f"{float(mclip.group(1)):g}%" if mclip else "25%")
        t2 = re.sub(r"\b(clip|take|my|initials?|out|of|the)\b", " ", t)
        ca, word = _target(t2, raw, c, core, reply_ca=reply_ca)
        if isinstance(word, dict) and word.get("ambiguous"):
            for h in word["ambiguous"]:
                if c.execute("select 1 from positions where ca=?", (h["ca"],)).fetchone(): ca = h["ca"]; break
        ca = ca or reply_ca
        if not ca:
            rows = c.execute("select ca from positions").fetchall()
            if len(rows) == 1: ca = rows[0]["ca"]
            else: return {"kind": "error", "msg": "Clip which token? Name the ticker / CA or reply to its message."}
        return {"kind": "trade", "side": "clip", "ca": ca, "spec": spec}
    side = "sell" if is_sell and (not is_buy or is_sell.start() <= is_buy.start()) else "buy"
    if side == "buy" and re.search(r"\btake profits?\b", t): side = "sell"
    ca, word = _target(t, raw, c, core, reply_ca=reply_ca)
    amb = isinstance(word, dict) and word.get("ambiguous")
    if amb:
        pass
    elif ca is None and word and not reply_ca:
        return {"kind": "error", "msg": f"I don't know a token called '{word}'. Use the contract address (0x… / Solana) or reply to its alert."}
    elif ca is None and word and re.search(rf"\b(of|on|in|into)\s+\$?{re.escape(str(word))}\b", t):
        return {"kind": "error", "msg": f"I don't know a token called '{word}'. Say/type the ticker again, use the CA, or say 'of it' when replying to an alert."}
    if ca is None and not amb: ca = reply_ca
    if ca is None and not amb and side == "buy": ca = recent_alert(c)
    if ca is None and not amb:
        rows = c.execute("select ca from positions").fetchall()
        if len(rows) == 1: ca = rows[0]["ca"]
        else: return {"kind": "error", "msg": "Which token? Reply to its alert/position message, or name the ticker / CA."}
    if side == "buy":
        nums = [float(a or b) for a, b in re.findall(r"\$\s?(\d+(?:\.\d+)?)|\b(\d+(?:\.\d+)?)\b(?!%)", re.sub(r"0x[0-9a-f]{40}|[1-9A-HJ-NP-Za-km-z]{32,44}", " ", t))]
        if not nums: return {"kind": "error", "msg": "How much? e.g. 'buy $100 of it'."}
        if amb:
            return {"kind": "ambiguous", "side": "buy", "usd": nums[0], "ticker": word["ticker"], "hits": word["ambiguous"]}
        return {"kind": "trade", "side": "buy", "ca": ca, "usd": nums[0]}
    s = re.sub(r"0x[0-9a-f]{40}|[1-9A-HJ-NP-Za-km-z]{32,44}", " ", t)
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m: amt = f"{float(m.group(1)):g}%"
    else:
        amt = next((v for rx, v in FRAC if re.search(rx, s)), None)
        if not amt:
            mu = re.search(r"\$\s?(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:bucks?|dollars?|usd)", s)
            if mu: amt = mu.group(1) or mu.group(2)
            elif re.search(ALL, s) or re.search(r"\b(close|exit|dump|bail|cash out|unload)\b", s): amt = "all"
            else: return {"kind": "error", "msg": "How much should I sell? e.g. 'sell half', 'sell 30%', 'sell all'."}
    if amt in ("100%",): amt = "all"
    if amb:
        # sell into an open namesake if any; else ask
        for h in word["ambiguous"]:
            if c.execute("select 1 from positions where ca=?", (h["ca"],)).fetchone():
                return {"kind": "trade", "side": "sell", "ca": h["ca"], "amt": amt}
        return {"kind": "error", "msg": f"${word['ticker']} matches multiple tokens and none are open. Use the CA to sell."}
    return {"kind": "trade", "side": "sell", "ca": ca, "amt": amt}
def describe(intent, core, c):
    sym = core.esc(core.symbol_of(c, intent["ca"]))
    if intent["side"] == "clip": what = f"CLIP <b>{'initial out' if intent['spec']=='initial' else intent['spec']}</b> of <b>{sym}</b>"
    elif intent["side"] == "buy": what = f"BUY <b>${intent['usd']:,.2f}</b> of <b>{sym}</b>"
    else:
        a = intent["amt"]; what = f"SELL <b>{'100%' if a == 'all' else (a if a.endswith('%') else '$' + a)}</b> of <b>{sym}</b>"
    dup = core.recent_trade(intent["ca"], intent["side"], 10, c) if intent["side"] != "clip" else None
    dup = dup if hasattr(core, "recent_trade") else None
    warn = f"\n⚠️ You already {'bought' if dup['side']=='buy' else 'sold'} {sym} at {dup['ts'][11:16]} {getattr(core, 'TZ_LABEL', '')} (${dup['usd_notional']:,.0f}). Tap Yes only if you want another." if dup else ""
    net = core.chain_of(c, intent["ca"]) if hasattr(core, "chain_of") else None
    return f"🤖 Confirm paper trade:\n{what} on <b>{net or '?'}</b>\n<code>{intent['ca']}</code>{warn}"
