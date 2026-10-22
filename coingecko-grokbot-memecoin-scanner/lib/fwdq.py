"""Retry queue for forwards to TELEGRAM_FORWARD_URL (research from discovery, free-form from telegram daemon).
sqlite at <repo>/fwdq.db. Backoff after failure n: 1,2,5,10 min then every 10 min; give up after 2h.
Research items older than 90 min (since first enqueue) are dropped as stale. Mirrors pending research to pending_research.json
so the 15-min backstop scan routine can pick them up. Key/URL from env only; never stored."""
import json, os, sqlite3, time, urllib.request, threading
import sys
sys.path.insert(0, os.path.dirname(__file__) or ".")
import addr as A
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
BASE = _ROOT; DB = os.environ.get("FWDQ_DB", f"{BASE}/fwdq.db"); PENDING = f"{BASE}/pending_research.json"
BACKOFF = [60, 120, 300, 600]; STEP = 600; MAX_AGE = 7200; RESEARCH_MAX_AGE = 5400
_L = threading.RLock()
def research_enabled():
    """Research forwarding toggle: risk.json discovery.research_forward (default True). False = discovery stops forwarding/queuing
    research and pending_research.json stays empty. Re-enable: set it to true (or remove the key) and restart discovery."""
    try: return json.load(open(BASE + "/risk.json")).get("discovery", {}).get("research_forward", True) is not False
    except Exception: return True
def _c():
    c = sqlite3.connect(DB, timeout=10); c.row_factory = sqlite3.Row
    c.execute("""create table if not exists q(id integer primary key autoincrement, kind text, dedupe text unique, body text, created real,
      attempts integer default 0, next_at real, last_status text, status text default 'pending', chat_id integer, notified integer default 0)"""); return c
def post(body, timeout=15):
    """-> (ok, status, err_text). Non-2xx / network errors are failures."""
    url, key = os.environ.get("TELEGRAM_FORWARD_URL"), os.environ.get("TELEGRAM_FORWARD_KEY", "")
    if not url: return False, "no-url", ""
    h = {"Content-Type": "application/json", "User-Agent": "cg-memecoin-scanner-fwdq/1"}
    if key: h["Authorization"] = f"Bearer {key}"; h["X-Api-Key"] = key
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body, default=str).encode(), headers=h, method="POST"), timeout=timeout) as r:
            return 200 <= r.status < 300, r.status, ""
    except Exception as e:
        try: eb = e.read()[:200].decode(errors="replace") if hasattr(e, "read") else str(e)[:200]
        except Exception: eb = ""
        if key: eb = eb.replace(key, "***")
        return False, getattr(e, "code", type(e).__name__), eb
def enqueue(kind, body, dedupe, status_txt="", chat_id=None, created=None):
    """Returns True if newly queued (False if already queued)."""
    if kind == "research" and not research_enabled(): return False
    with _L:
        c = _c()
        try:
            cur = c.execute("insert or ignore into q(kind,dedupe,body,created,attempts,next_at,last_status,chat_id) values(?,?,?,?,1,?,?,?)",
                            (kind, dedupe, json.dumps(body, default=str), created or time.time(), time.time() + BACKOFF[0], str(status_txt)[:200], chat_id))
            c.commit(); new = cur.rowcount > 0
        finally: c.close()
    write_pending(); return new
def _delay(n): return BACKOFF[n - 1] if n <= len(BACKOFF) else STEP
def drain(log=print, on_sent=None, kind=None):
    """Retry due items once. on_sent(row) is called after a successful resend."""
    now = time.time(); sent = 0
    if kind == "research" and not research_enabled(): write_pending(); return 0
    if not os.environ.get("TELEGRAM_FORWARD_URL"): write_pending(); return 0   # local-queue mode: the scheduled scan routine handles items
    with _L:
        c = _c()
        try:
            for r in c.execute("select * from q where status='pending' and (? is null or kind=?)", (kind, kind)).fetchall():
                age = now - r["created"]
                if (r["kind"] == "research" and age > RESEARCH_MAX_AGE) or age > MAX_AGE:
                    c.execute("update q set status='dropped-stale' where id=?", (r["id"],)); log("fwdq drop stale", r["kind"], r["dedupe"][:24]); continue
                if r["next_at"] > now: continue
                ok, st, eb = post(json.loads(r["body"]))
                if ok:
                    c.execute("update q set status='sent', last_status=? where id=?", (str(st), r["id"])); sent += 1; log("fwdq sent", r["kind"], r["dedupe"][:24], "after", r["attempts"], "fails")
                    if on_sent:
                        try: on_sent(dict(r))
                        except Exception as e: log("fwdq on_sent err", e)
                else:
                    n = r["attempts"] + 1
                    c.execute("update q set attempts=?, next_at=?, last_status=? where id=?", (n, now + _delay(n), f"{st} {eb}"[:200], r["id"])); log("fwdq retry fail", r["kind"], r["dedupe"][:24], st, "next in", _delay(n) // 60, "min")
            c.commit()
        finally: c.close()
    write_pending(); return sent
def write_pending():
    try:
        if not research_enabled():
            tmp = PENDING + ".tmp"; json.dump({"updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": "Research forwarding is OFF (risk.json discovery.research_forward=false). Nothing to handle.", "items": []}, open(tmp, "w"), indent=1); os.replace(tmp, PENDING); return
        c = _c(); rows = c.execute("select * from q where status='pending' and kind='research' order by created").fetchall(); c.close()
        now = time.time(); items = []
        for r in rows:
            if now - r["created"] > RESEARCH_MAX_AGE: continue
            b = json.loads(r["body"])
            items.append({"ca": b.get("ca"), "network": b.get("network"), "symbol": (b.get("token") or {}).get("symbol"), "prelim_verdict": b.get("prelim_verdict"),
                          "score": b.get("score"), "payload_file": f"research/{b.get('network')}_{b.get('ca')}.json", "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(r["created"])),
                          "attempts": r["attempts"], "last_status": r["last_status"]})
        try:   # x-first queue (xfirst/xfirst.py) is mirrored here too
            for x in json.load(open(BASE + "/xfirst/queue.json")):
                if x.get("status") == "pending": items.append(dict(x))
        except Exception: pass
        tmp = PENDING + ".tmp"; json.dump({"updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": "Research waiting for the scheduled scan (queued locally, or the webhook rejected it). Scan routine: handle each (X buzz + narrative + send_card), then run `python3 lib/fwdq.py done <ca>`.", "items": items}, open(tmp, "w"), indent=1); os.replace(tmp, PENDING)
    except Exception: pass
def done(ca):
    with _L:
        c = _c(); n = c.execute("update q set status='handled-by-scan' where status='pending' and kind='research' and dedupe like ?", (f"research:{A.norm(ca)}%",)).rowcount; c.commit(); c.close()
    try:
        qp = BASE + "/xfirst/queue.json"; xq = json.load(open(qp))
        for x in xq:
            if x.get("status") == "pending" and A.same(x.get("ca",""), ca): x["status"] = "done"; n += 1
        json.dump(xq, open(qp, "w"), indent=1)
    except Exception: pass
    write_pending(); return n
if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["done"]: print(done(sys.argv[2]))
    elif sys.argv[1:2] == ["list"]:
        c = _c(); print(json.dumps([{k: r[k] for k in r.keys() if k != "body"} for r in c.execute("select * from q order by id desc limit 30")], indent=1))
