#!/usr/bin/env python3
"""Wallet-intelligence DB for the memecoin scanner.
Commands:
  init
  upsert            < JSON {"wallets":[...], "sightings":[...], "clusters":[...]}
  lookup ADDR...    (or JSON list on stdin)  -> known labels
  score-token       < JSON {"token":ca,"chain":..,"wallets":[{address,first_trade_time?,block?,holding_pct?,funder?,bought?}]}
  top [--n 20] [--chain X]
  clusters
  stats
"""
import sqlite3, json, sys, os, argparse, datetime, statistics, time
import os as _os; _ROOT = _os.environ.get("MEMESCAN_HOME") or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "."))
sys.path.insert(0, _ROOT + "/lib"); import addr as A
DB = os.environ.get("WALLETDB", _ROOT + "/wallets.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets(
 address TEXT PRIMARY KEY, chains TEXT, label TEXT, confidence TEXT,
 skill_score REAL, win_rate REAL, realized_pnl REAL, total_tokens INTEGER,
 chains_active INTEGER, first_seen TEXT, last_seen TEXT, times_seen INTEGER DEFAULT 0,
 tokens_seen INTEGER DEFAULT 0, smart_evidence INTEGER DEFAULT 0, notes TEXT);
CREATE TABLE IF NOT EXISTS sightings(
 id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT, token_ca TEXT, chain TEXT, pool TEXT,
 role TEXT, pnl_on_token REAL, bought INTEGER, first_trade_time TEXT, verdict_of_token TEXT,
 seen_at TEXT, UNIQUE(address, token_ca, chain, role));
CREATE TABLE IF NOT EXISTS clusters(
 cluster_id TEXT PRIMARY KEY, reason TEXT, members TEXT, created_at TEXT, notes TEXT);
CREATE INDEX IF NOT EXISTS ix_s_addr ON sightings(address);
CREATE INDEX IF NOT EXISTS ix_s_tok ON sightings(token_ca);
CREATE TABLE IF NOT EXISTS wallet_history(
 address TEXT, chain TEXT, built_at TEXT, window_days INTEGER, summary TEXT, tokens TEXT, PRIMARY KEY(address, chain));
"""
BOTISH = {"bot", "infra", "mev"}
def now(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def conn():
    c = sqlite3.connect(DB, timeout=30); c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=30000")
    for i in range(5):
        try: c.execute("PRAGMA journal_mode=WAL"); c.executescript(SCHEMA); break
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) or i == 4: raise
            time.sleep(1 + i)
    return c
def L(a, chain=None): return A.norm(a, chain)   # EVM lowercase, Solana base58 case preserved
def is_prefix(m): return not (A.is_evm(m) or A.is_sol(m))

def skill(win, pnl, n):
    if win is None: return None
    return round(win*50 + min(max(pnl or 0, 0), 50000)/50000*30 + min(n or 0, 20)/20*20, 1)

def auto_label(w):
    """Apply playbook rules when label not given. Returns (label, confidence)."""
    tt, ch = w.get("total_tokens"), w.get("chains_active")
    if w.get("trades_per_token", 0) > 1500 or w.get("trades_per_day", 0) > 50 or (tt or 0) > 5000 or ((ch or 0) >= 3 and (tt or 0) > 300):
        return "bot", "high"
    if w.get("never_bought_holding_pct", 0) >= 0.5 or w.get("sell_only_from_creation"):
        return "insider", "high"
    if (w.get("closed_trades") or 0) >= 5 and (w.get("win_rate") or 0) >= 0.6 and (w.get("realized_pnl") or 0) > 0:
        return "proven_candidate", "low"   # promoted to smart_money only via repeated evidence
    if w.get("sniper"): return "sniper", "medium"
    return "unknown", "low"

def upsert(data):
    c = conn(); t = now(); n_w = n_s = n_c = 0
    for w in data.get("wallets", []):
        a = L(w["address"], w.get("chain"));
        if not a: continue
        lab, conf = (w.get("label"), w.get("confidence", "medium")) if w.get("label") else auto_label(w)
        ss = w.get("skill_score") or skill(w.get("win_rate"), w.get("realized_pnl"), w.get("closed_trades"))
        r = c.execute("SELECT * FROM wallets WHERE address=?", (a,)).fetchone()
        chains = set((r["chains"] or "").split(",")) if r else set()
        chains |= set(x for x in (w.get("chains") or w.get("chain") or "").split(",") if x)
        chains.discard("")
        ev = (r["smart_evidence"] if r else 0) + (1 if lab == "proven_candidate" else 0)
        if r:
            old = r["label"]
            # never downgrade a hard negative label to a softer one automatically
            if old in ("bot", "infra", "insider") and lab in ("unknown", "proven_candidate", "sniper", "smart_money"):
                lab, conf = old, r["confidence"]
            elif lab in ("unknown",) and old: lab, conf = old, r["confidence"]
            notes = r["notes"] or ""
            if w.get("notes") and w["notes"] not in notes: notes = (notes + " | " + w["notes"]).strip(" |")
            c.execute("""UPDATE wallets SET chains=?,label=?,confidence=?,skill_score=COALESCE(?,skill_score),
              win_rate=COALESCE(?,win_rate),realized_pnl=COALESCE(?,realized_pnl),total_tokens=COALESCE(?,total_tokens),
              chains_active=COALESCE(?,chains_active),last_seen=?,times_seen=times_seen+1,smart_evidence=?,notes=? WHERE address=?""",
              (",".join(sorted(chains)), lab, conf, ss, w.get("win_rate"), w.get("realized_pnl"), w.get("total_tokens"),
               w.get("chains_active"), t, ev, notes, a))
        else:
            c.execute("""INSERT INTO wallets(address,chains,label,confidence,skill_score,win_rate,realized_pnl,total_tokens,
              chains_active,first_seen,last_seen,times_seen,smart_evidence,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
              (a, ",".join(sorted(chains)), lab, conf, ss, w.get("win_rate"), w.get("realized_pnl"), w.get("total_tokens"),
               w.get("chains_active"), w.get("first_seen", t), t, ev, w.get("notes")))
        n_w += 1
    for s in data.get("sightings", []):
        a = L(s["address"], s.get("chain"))
        c.execute("""INSERT INTO sightings(address,token_ca,chain,pool,role,pnl_on_token,bought,first_trade_time,verdict_of_token,seen_at)
          VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(address,token_ca,chain,role) DO UPDATE SET
          pnl_on_token=COALESCE(excluded.pnl_on_token,pnl_on_token), verdict_of_token=COALESCE(excluded.verdict_of_token,verdict_of_token),
          bought=COALESCE(excluded.bought,bought), seen_at=excluded.seen_at""",
          (a, L(s.get("token_ca"), s.get("chain")), s.get("chain"), L(s.get("pool"), s.get("chain")), s.get("role"), s.get("pnl_on_token"),
           None if s.get("bought") is None else int(bool(s["bought"])), s.get("first_trade_time"), s.get("verdict_of_token"), s.get("seen_at", t)))
        if not c.execute("SELECT 1 FROM wallets WHERE address=?", (a,)).fetchone():
            c.execute("INSERT INTO wallets(address,chains,label,confidence,first_seen,last_seen,times_seen) VALUES(?,?,?,?,?,?,1)",
                      (a, s.get("chain"), "unknown", "low", t, t))
        n_s += 1
    for cl in data.get("clusters", []):
        mem = sorted(set(L(m) for m in cl.get("members", [])))
        r = c.execute("SELECT members FROM clusters WHERE cluster_id=?", (cl["cluster_id"],)).fetchone()
        if r: mem = sorted(set(json.loads(r["members"])) | set(mem))
        c.execute("INSERT OR REPLACE INTO clusters VALUES(?,?,?,?,?)",
                  (cl["cluster_id"], cl.get("reason"), json.dumps(mem), cl.get("created_at", t), cl.get("notes")))
        n_c += 1
    refresh_evidence(c); c.commit()
    print(json.dumps({"wallets": n_w, "sightings": n_s, "clusters": n_c}))

def refresh_evidence(c):
    """tokens_seen + promotion: proven_candidate -> smart_money when profitable (bought, pnl>0) on >=3 distinct tokens
    across >=2 scans with no bot/insider flag; demote to bot if seen in >=10 tokens within 24h."""
    c.execute("""UPDATE wallets SET tokens_seen=(SELECT COUNT(DISTINCT token_ca) FROM sightings s WHERE s.address=wallets.address)""")
    rows = c.execute("""SELECT address, COUNT(DISTINCT token_ca) n FROM sightings WHERE bought=1 AND pnl_on_token>0 GROUP BY address""").fetchall()
    for r in rows:
        w = c.execute("SELECT label,smart_evidence FROM wallets WHERE address=?", (r["address"],)).fetchone()
        if w and w["label"] in ("proven_candidate", "unknown", "sniper") and r["n"] >= 3 and (w["smart_evidence"] or 0) >= 1:
            c.execute("UPDATE wallets SET label='smart_money', confidence=? WHERE address=?", ("high" if r["n"] >= 5 else "medium", r["address"]))

def cluster_map(c):
    m = {}
    for r in c.execute("SELECT cluster_id, members FROM clusters"):
        for a in json.loads(r["members"]): m.setdefault(a, []).append(r["cluster_id"])
    return m

def lookup(addrs):
    c = conn(); cm = cluster_map(c); out = {}
    for a in map(L, addrs):
        r = c.execute("SELECT * FROM wallets WHERE address=?", (a,)).fetchone()
        if r:
            d = dict(r); d["clusters"] = cm.get(a, [])
            d["recent_tokens"] = [dict(x) for x in c.execute(
                "SELECT token_ca,chain,role,pnl_on_token,bought,verdict_of_token FROM sightings WHERE address=? ORDER BY seen_at DESC LIMIT 5", (a,))]
            out[a] = d
        else:
            pre = [cid for cid, in c.execute("SELECT cluster_id FROM clusters WHERE reason LIKE 'vanity prefix%'")
                   if any(a.startswith(p) for p in json.loads(c.execute("SELECT members FROM clusters WHERE cluster_id=?", (cid,)).fetchone()[0]) if is_prefix(p))]
            out[a] = {"known": False, "prefix_clusters": pre} if pre else None
    print(json.dumps(out, indent=1, default=str))

def to_ts(x):
    if x is None: return None
    if isinstance(x, (int, float)): return float(x)
    try: return datetime.datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp()
    except Exception: return None

TRANSIENT = ("within_", "near_equal_holdings", "same_block")   # per-token timing/size coincidences: never carried across tokens

def _similar(ws_by, members, tol=0.5):
    """members whose buy size is within +-tol of the group median (needs buy sizes; unknown sizes count as similar)."""
    sz = [ws_by[a].get("buy") for a in members if ws_by[a].get("buy")]
    if len(sz) < 3: return members
    med = statistics.median(sz)
    return [a for a in members if not ws_by[a].get("buy") or abs(ws_by[a]["buy"] - med) <= tol * med]

def detect_bundles(ws, sec=5, eq_tol=0.05, chain=None, max_chain=8):
    groups = []; ws_by = {L(w["address"]): w for w in ws}
    min_block = 4 if (chain or "").lower() == "robinhood" else 3
    by_block = {}
    for w in ws:
        if w.get("block") is not None: by_block.setdefault(w["block"], []).append(L(w["address"]))
    for b, m in by_block.items():
        m2 = _similar(ws_by, m, 0.35)
        if len(m2) >= min_block: groups.append(("same_block:%s" % b, m2))
    tw = sorted([(to_ts(w.get("first_trade_time") or w.get("first_seen")), L(w["address"])) for w in ws if to_ts(w.get("first_trade_time") or w.get("first_seen"))])
    def flush(cur):
        if len(cur) < 3 or len(cur) > max_chain: return   # long chains = busy launch tape, not a bundle
        m2 = _similar(ws_by, [x[1] for x in cur], 0.35)
        if len(m2) >= 3: groups.append(("within_%ss" % sec, m2))
    cur = []
    for t, a in tw:
        if cur and t - cur[-1][0] > sec: flush(cur); cur = []
        cur.append((t, a))
    flush(cur)
    fund = {}
    for w in ws:
        if w.get("funder"): fund.setdefault(L(w["funder"]), []).append(L(w["address"]))
    groups += [("shared_funder:%s" % f, m) for f, m in fund.items() if len(m) >= 2]
    hp = sorted([(w["holding_pct"], L(w["address"])) for w in ws if w.get("holding_pct")])
    cur = []
    for p, a in hp:
        if cur and abs(p - cur[0][0]) / max(cur[0][0], 1e-9) > eq_tol:
            if len(cur) >= 3: groups.append(("near_equal_holdings", [x[1] for x in cur]))
            cur = []
        cur.append((p, a))
    if len(cur) >= 3 and cur[0][0] >= 0.2: groups.append(("near_equal_holdings", [x[1] for x in cur]))
    return groups

def relevant_clusters(c, addrs, token):
    """past clusters that matter for THIS token: same token/launch (cluster_id or notes carry its CA prefix), or >=2 other
    members also present among this token's wallets. Transient (timing/size) clusters from other tokens are ignored."""
    tok = (token or "").strip().lower()[:10]; aset = set(addrs); rel = {}
    for r in c.execute("SELECT cluster_id, reason, members, notes FROM clusters"):
        mem = set(json.loads(r["members"])); hit = mem & aset
        if not hit: continue
        same_tok = bool(tok) and (tok in (r["cluster_id"] or "").lower() or tok in (r["notes"] or "").lower())
        if not same_tok and any((r["reason"] or "").startswith(x) for x in TRANSIENT): continue
        if same_tok or len(hit) >= 3:   # the wallet itself + >=2 other members here
            for a in hit: rel.setdefault(a, []).append(r["cluster_id"])
    return rel

def score_token(data, save=False):
    c = conn(); cm = cluster_map(c); ws = data.get("wallets", [])
    bundles = detect_bundles(ws, chain=data.get("chain"))
    rel = relevant_clusters(c, [L(w["address"]) for w in ws], data.get("token"))
    in_bundle = set(a for _, m in bundles for a in m)
    mix = {"smart": 0, "human": 0, "bot": 0, "insider": 0, "bundle": 0, "unknown": 0}; detail = {}
    for w in ws:
        a = L(w["address"], w.get("chain")); r = c.execute("SELECT label,confidence FROM wallets WHERE address=?", (a,)).fetchone()
        lab = r["label"] if r else "unknown"
        pref = [cid for m, cids in cm.items() if is_prefix(m) and a.startswith(m) for cid in cids]
        if not r and pref: lab = "infra" if any("launchpad" in x for x in pref) else "insider"
        if lab in BOTISH: k = "bot"
        elif lab == "insider" or w.get("bought") is False: k = "insider"
        elif a in in_bundle or rel.get(a): k = "bundle"
        elif lab == "smart_money": k = "smart"
        elif lab in ("proven_candidate", "holder", "human", "flipper", "sniper") : k = "human"
        else: k = "unknown"
        mix[k] += 1; detail[a] = {"class": k, "label": lab, "clusters": rel.get(a, [])}
    n = max(len(ws), 1)
    # human participation: smart/human count fully, unknowns 0.6 (unproven, DB still young), bot/insider/bundle zero
    hp = round(100 * (mix["smart"] + mix["human"] + 0.6 * mix["unknown"]) / n, 1)
    tag = ("bot/bundle dominated" if (mix["bot"] + mix["bundle"]) / n >= 0.5 else
           "insider heavy" if mix["insider"] / n >= 0.3 else
           "smart money present" if mix["smart"] >= 2 else
           "mostly human" if hp >= 60 else "mixed")
    res = {"token": data.get("token"), "chain": data.get("chain"), "n_wallets": len(ws), "mix": mix,
           "human_participation": hp, "read": tag, "bundles": [{"reason": r, "members": m} for r, m in bundles],
           "detail": detail}
    if save and bundles:
        for i, (r, m) in enumerate(bundles):
            c.execute("INSERT OR REPLACE INTO clusters VALUES(?,?,?,?,?)",
                      ("%s_%s_%d" % (data.get("chain"), L(data.get("token"), data.get("chain"))[:10], i), r, json.dumps(sorted(m)), now(), "auto from score-token"))
        c.commit()
    print(json.dumps(res, indent=1))

def top(n, chain):
    c = conn(); q = "SELECT address,chains,label,confidence,skill_score,win_rate,realized_pnl,tokens_seen,times_seen,notes FROM wallets WHERE label IN ('smart_money','proven_candidate')"
    args = []
    if chain: q += " AND chains LIKE ?"; args.append("%" + chain + "%")
    q += " ORDER BY (label='smart_money') DESC, skill_score DESC, tokens_seen DESC LIMIT ?"; args.append(n)
    print(json.dumps([dict(r) for r in c.execute(q, args)], indent=1))

def clusters():
    c = conn(); print(json.dumps([dict(r, members=json.loads(r["members"])) for r in c.execute("SELECT * FROM clusters")], indent=1))

def stats():
    c = conn()
    print(json.dumps({"wallets": c.execute("SELECT COUNT(*) FROM wallets").fetchone()[0],
      "by_label": dict(c.execute("SELECT label,COUNT(*) FROM wallets GROUP BY label").fetchall()),
      "sightings": c.execute("SELECT COUNT(*) FROM sightings").fetchone()[0],
      "clusters": c.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]}, indent=1))

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("cmd"); p.add_argument("args", nargs="*")
    p.add_argument("--n", type=int, default=20); p.add_argument("--chain"); p.add_argument("--save", action="store_true")
    o = p.parse_args()
    stdin = lambda: json.load(sys.stdin)
    if o.cmd == "init": conn().commit(); print("ok", DB)
    elif o.cmd == "upsert": upsert(stdin())
    elif o.cmd == "lookup": lookup(o.args or stdin())
    elif o.cmd == "score-token": score_token(stdin(), o.save)
    elif o.cmd == "top": top(o.n, o.chain)
    elif o.cmd == "clusters": clusters()
    elif o.cmd == "stats": stats()
    else: p.error("unknown cmd")
