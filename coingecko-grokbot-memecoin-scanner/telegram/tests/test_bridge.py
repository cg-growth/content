"""Dry-run tests: throwaway DB + muted file, Telegram and price calls mocked. No network, no real messages.
Run: python3 -m pytest -q tests/  (or python3 tests/test_bridge.py)"""
import os, sys, tempfile, json
D = tempfile.mkdtemp(); os.environ["PAPER_DB"] = f"{D}/paper.db"; os.environ["TG_MUTED_FILE"] = f"{D}/muted.json"
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "TESTTOKEN"); os.environ["TG_DRY_RUN"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core, nl, daemon
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OWN = 123456789; ALT = "0x" + "a" * 40; AXI = "0x" + "b" * 40
CALLS = []; MID = [1000]
def fake_tg(method, timeout=40, **p):
    CALLS.append((method, p)); MID[0] += 1
    return {"ok": True, "result": {"message_id": MID[0]}}
core.tg = fake_tg; daemon.core.tg = fake_tg
class _Sync:   # run handlers inline so assertions see their Telegram calls
    def submit(self, f, *a, **k): f(*a, **k)
daemon.POOL = _Sync()
core.owner = lambda: {"chat_id": OWN}
PX = {ALT: 0.01, AXI: 2.0}
core.quote = lambda ca, chain=None: {"network": "robinhood", "ca": ca, "symbol": {ALT: "ALTAI", AXI: "AXIS"}[ca], "price": PX[ca], "liquidity": 500000, "pool": "0xpool"} if ca in PX else None
def setup():
    c = core.db()
    for i, (ca, sym) in enumerate([(ALT, "ALTAI"), (AXI, "AXIS")]):
        c.execute("insert or replace into alerts values(?,?,?,?,?,?,?,?,?,?,?)", (500 + i, OWN, ca, "robinhood", "0xpool", sym, "Watch", "low", 55, "<b>ALERT</b>", core.now()))
    c.commit(); return c
c = setup()
def P(t, rca=None): return nl.parse(t, rca, c, core)
def test_nl():
    assert P("buy 200 bucks of altai") == {"kind": "trade", "side": "buy", "ca": ALT, "usd": 200.0}
    assert P("grab $50 more", ALT) == {"kind": "trade", "side": "buy", "ca": ALT, "usd": 50.0}
    assert P("Buy fifty dollars of AXIS")["usd"] == 50 and P("buy fifty dollars of axis")["ca"] == AXI
    assert P("ape 1k into $altai")["usd"] == 1000
    assert P("sell half", ALT) == {"kind": "trade", "side": "sell", "ca": ALT, "amt": "50%"}
    assert P("dump it all", AXI)["amt"] == "all"
    assert P("close axis") == {"kind": "trade", "side": "sell", "ca": AXI, "amt": "all"}
    assert P("take profits 30%", ALT)["amt"] == "30%"
    assert P("Take profits thirty percent on altai")["amt"] == "30%"
    assert P("sell a quarter of altai")["amt"] == "25%"
    assert P(f"buy 75 {AXI}")["ca"] == AXI
    assert P("how am I doing?") == {"kind": "query", "cmd": "pnl"}
    assert P("what's my pnl") == {"kind": "query", "cmd": "pnl"}
    assert P("show positions") == {"kind": "query", "cmd": "positions"}
    assert P("what's my balance")["cmd"] == "balance"
    assert P("buy 100 of zzzcoin")["kind"] == "error"
    assert P("Let's get into ALTAI, $50") == {"kind": "trade", "side": "buy", "ca": ALT, "usd": 50.0}
    assert P("ape altai 50")["usd"] == 50 and P("put 50 in axis")["ca"] == AXI
    assert P("jump into axis with 25")["usd"] == 25
    assert P("but $50 of it", ALT) == {"kind": "trade", "side": "buy", "ca": ALT, "usd": 50.0}
    assert P("but why did it dump") is None and P("should I sell half?") is None
    assert P("sell half?", ALT)["amt"] == "50%"
    assert P("sell some", ALT)["kind"] == "error"
    assert P("buy altai")["kind"] == "error"
    # unknown words + reply-to alert -> trades the replied-to alert CA (current behaviour)
    assert P("buy 200 dollars on moral tie", ALT)["ca"] == ALT
    assert P("buy 200 of it", ALT)["ca"] == ALT
    assert P("gm what do you think about the market") is None
def upd_msg(text=None, reply_to=None, **kw):
    m = {"message_id": MID[0] + 50, "chat": {"id": OWN, "type": "private"}, "from": {"id": OWN}, **kw}
    if text is not None: m["text"] = text
    if reply_to: m["reply_to_message"] = {"message_id": reply_to}
    MID[0] += 100; return {"message": m}
def cb(data, mid, text=""): return {"callback_query": {"id": "q", "from": {"id": OWN}, "data": data, "message": {"message_id": mid, "chat": {"id": OWN}, "text": text}}}
def methods(): return [m for m, _ in CALLS]
def test_flow():
    CALLS.clear(); daemon.dispatch(cb(f"b:100:{ALT}", 500))
    assert methods()[:3] == ["answerCallbackQuery", "sendMessage", "editMessageText"], methods()
    assert "Your position" in CALLS[2][1]["text"] and "inline_keyboard" in CALLS[2][1]["reply_markup"]
    c2 = core.db(); assert c2.execute("select count(*) from positions").fetchone()[0] == 1
    # NL with confirmation
    CALLS.clear(); daemon.dispatch(upd_msg("sell half", reply_to=500))
    assert methods() == ["sendMessage"] and "Confirm" in CALLS[0][1]["text"]
    yes = CALLS[0][1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
    assert c2.execute("select count(*) from trades").fetchone()[0] == 1   # nothing executed yet
    CALLS.clear(); daemon.dispatch(cb(yes, 1, "🤖 Confirm paper trade:\nSELL 50%"))
    assert c2.execute("select count(*) from trades where side='sell'").fetchone()[0] == 1
    CALLS.clear(); daemon.dispatch(cb(yes, 1)); assert "already" in CALLS[0][1]["text"]   # no double execution
    # No -> cancelled
    CALLS.clear(); daemon.dispatch(upd_msg("buy 200 bucks of axis")); no = CALLS[0][1]["reply_markup"]["inline_keyboard"][0][1]["callback_data"]
    daemon.dispatch(cb(no, 2)); assert c2.execute("select count(*) from positions where ca=?", (AXI,)).fetchone()[0] == 0
    # custom force_reply
    CALLS.clear(); daemon.dispatch(cb(f"c:{AXI}", 501)); prompt_mid = MID[0]
    assert CALLS[1][1]["reply_markup"]["force_reply"] is True
    daemon.dispatch(upd_msg("75", reply_to=prompt_mid)); assert c2.execute("select cost_usd from positions where ca=?", (AXI,)).fetchone()[0] == 75
    # positions with per-position buttons; sell all from there
    CALLS.clear(); daemon.dispatch(upd_msg("/positions")); kb = CALLS[0][1]["reply_markup"]["inline_keyboard"]
    assert len(kb) == 3 and kb[1][2]["callback_data"] == f"s:all:{AXI}"; pmid = MID[0]
    CALLS.clear(); daemon.dispatch(cb(f"s:all:{AXI}", pmid)); assert "editMessageText" in methods()
    assert c2.execute("select count(*) from positions where ca=?", (AXI,)).fetchone()[0] == 0
    # sell button with no position -> toast only
    CALLS.clear(); daemon.dispatch(cb(f"s:50:{AXI}", 501)); assert methods() == ["answerCallbackQuery"]
    # mute toggle
    daemon.dispatch(cb(f"m:{AXI}", 501)); assert core.is_muted(AXI) and json.load(open(os.environ["TG_MUTED_FILE"]))
    daemon.dispatch(cb(f"m:{AXI}", 501)); assert not core.is_muted(AXI)
    # queries, legacy reply, fallback hint (no forward URL)
    CALLS.clear(); daemon.dispatch(upd_msg("how am i doing")); assert "PnL" in CALLS[0][1]["text"]
    CALLS.clear(); daemon.dispatch(upd_msg("buy 10", reply_to=501)); assert "PAPER BUY" in CALLS[0][1]["text"]
    os.environ.pop("TELEGRAM_FORWARD_URL", None)
    CALLS.clear(); daemon.dispatch(upd_msg("gm ser what's the vibe")); assert "didn't catch" in CALLS[0][1]["text"]
    os.environ["TELEGRAM_FORWARD_URL"] = "https://example.invalid/hook"; os.environ["TELEGRAM_FORWARD_KEY"] = "SECRETKEY"
    CALLS.clear(); daemon.dispatch(upd_msg("gm ser what's the vibe")); assert CALLS[0][1]["text"].startswith("⏳ On it, researching")
    os.environ.pop("TELEGRAM_FORWARD_URL"); os.environ.pop("TELEGRAM_FORWARD_KEY")
    # unauthorized button
    CALLS.clear(); daemon.dispatch({"callback_query": {"id": "q", "from": {"id": 1}, "data": f"b:50:{ALT}", "message": {"message_id": 500, "chat": {"id": 1}}}})
    assert methods() == ["answerCallbackQuery"] and CALLS[0][1]["text"] == "unauthorized"
def test_report():
    import tg_ext
    assert P("report card")["cmd"] == "report" and P("how did I do?")["cmd"] == "report" and P("how am i doing")["cmd"] == "pnl"
    sent = []; tg_ext.report = lambda cid, rt=None: sent.append(("report", rt)); tg_ext.portfolio = lambda cid, rt=None: sent.append(("pf", rt))
    daemon.dispatch(upd_msg("🧾 Report Card")); daemon.dispatch(upd_msg("/report")); daemon.dispatch(upd_msg("📊 Portfolio"))
    assert [k for k, _ in sent] == ["report", "report", "pf"]
    CALLS.clear(); daemon.dispatch(upd_msg("📈 Positions")); assert CALLS and CALLS[0][0] == "sendMessage"
    CALLS.clear(); daemon.dispatch({"callback_query": {"id": "q", "from": {"id": OWN}, "data": "rc", "message": {"message_id": 900, "chat": {"id": OWN}}}})
    assert sent[-1][0] == "report"
    # report data: round trips incl. partial + full exits, exit reasons
    sys.path.insert(0, _ROOT + "/alerts"); import report as R
    cc = core.db()
    cl = R.closed_trades(cc); d = R.data()
    assert all(x["why"] in R.RC for x in cl) and (d["wr"] is None) == (not cl)
    assert R.reason("risk-trail") == "TRAIL" and R.reason("risk-sl") == "SL" and R.reason("risk-liq_pull") == "DANGER" and R.reason("tp-confirm") == "TP" and R.reason("button") == "MANUAL"
    html = R.html_doc(d); assert "Report Card" in html and "Closed trades" in html
    e = R.html_doc({**d, "cl": [], "W": [], "L": [], "wr": None, "aw": None, "al": None, "pf": None, "best": None, "worst": None})
    assert "No closed trades yet" in e
def test_recent_trade():
    assert core.recent_trade("0x" + "c" * 40, "buy") is None
    c2 = core.db(); c2.execute("insert into trades(ts,side,ca,symbol,usd_notional,source) values(?,?,?,?,?,?)", (core.now(), "buy", "0x" + "c" * 40, "CCC", 50, "test")); c2.commit()
    assert core.recent_trade("0x" + "C" * 40, "buy")["usd_notional"] == 50 and core.recent_trade("0x" + "c" * 40, "sell") is None
if __name__ == "__main__":
    test_nl(); test_flow(); test_report(); test_recent_trade(); print("ALL OK")
