"""Per-trade feature snapshot for the AI paper book (auto.db).

One row per buy, keyed by buy_trade_id, plus one row per skipped or discarded
candidate. The research JSON is copied at decision time so a later re-research
does not rewrite history. Hold updates (max gain, drawdown, liquidity) and
post-exit prices at about 1h, 6h and 24h are filled by the risk engine and the
existing outcome tracker. No extra poll loop.
"""
import json, os, sqlite3, time, datetime as D

SCHEMA = """
create table if not exists trade_features(
  id integer primary key autoincrement,
  buy_trade_id integer,
  ca text not null,
  network text,
  pool text,
  symbol text,
  decided_at text,
  kind text,
  tier text,
  verdict_source text,
  ai_verdict text,
  ai_reason text,
  early_verdict text,
  research_json text,
  liq real,
  fdv real,
  liq_fdv real,
  pool_age_min real,
  chain text,
  dex text,
  launchpad text,
  buyers_h1 real,
  sellers_h1 real,
  buys_h1 real,
  sells_h1 real,
  vol_h1 real,
  vol_liq real,
  m5_change real,
  h1_change real,
  flow_buy_share real,
  top10_pct real,
  dev_pct real,
  holder_count real,
  gt_score real,
  gt_score_details text,
  is_honeypot integer,
  is_nsfw integer,
  human_score real,
  human_source text,
  artificial_score real,
  artificial_band text,
  artificial_reasons text,
  x_authors real,
  x_fields text,
  entry_px real,
  max_gain_pct real,
  max_drawdown_pct real,
  time_to_peak_s real,
  peak_px real,
  trough_px real,
  min_liq real,
  liq_drop_pct real,
  liq_events text,
  exit_reason text,
  exit_ts text,
  exit_return_pct real,
  px_1h real,
  px_6h real,
  px_24h real,
  ret_1h real,
  ret_6h real,
  ret_24h real,
  ref_px real,
  ref_ts text,
  ai_later text
);
create index if not exists trade_features_ca on trade_features(ca, decided_at);
"""


def _f(x):
    try:
        if x is None or x == "": return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _boolish(x):
    if x is None: return None
    if x is True: return 1
    if x is False: return 0
    return None


def ensure(c):
    c.executescript(SCHEMA)
    cols = {r[1] for r in c.execute("pragma table_info(trade_features)")}
    if "ai_later" not in cols:
        try: c.execute("alter table trade_features add column ai_later text")
        except Exception: pass
    return c


def _holders_count(token):
    h = (token or {}).get("holders")
    if isinstance(h, (int, float)): return float(h)
    if isinstance(h, dict):
        for k in ("count", "total", "holders"):
            if _f(h.get(k)) is not None: return _f(h.get(k))
    return None


def _top10(r):
    h = r.get("holders") or {}
    if h.get("top10_pct_ex_pools") is not None: return _f(h.get("top10_pct_ex_pools"))
    return _f(h.get("top10_pct_approx"))


def _x(r):
    out = {}
    buzz = r.get("buzz") if isinstance(r.get("buzz"), dict) else {}
    for k in ("unique_authors", "authors", "score", "grade", "posts", "quality"):
        if buzz.get(k) is not None: out["buzz_" + k] = buzz[k]
    for k in ("x_ca_authors", "x_authors", "x_quality"):
        if r.get(k) is not None: out[k] = r[k]
    b = r.get("_buzz") or {}
    if isinstance(b, dict) and b.get("authors") is not None:
        out["ca_buzz_authors"] = b.get("authors")
    authors = out.get("x_ca_authors")
    if authors is None: authors = out.get("ca_buzz_authors")
    if authors is None: authors = out.get("buzz_unique_authors")
    if authors is None and isinstance(buzz.get("authors"), (int, float)): authors = buzz.get("authors")
    return _f(authors), out


def _launchpad(token, r):
    if r.get("launchpad"): return str(r.get("launchpad"))[:120]
    cats = (token or {}).get("categories")
    if isinstance(cats, list) and cats: return ", ".join(str(x) for x in cats[:4])[:160]
    if isinstance(cats, str) and cats: return cats[:160]
    return None


def _dex(r):
    if r.get("dex"): return str(r.get("dex"))[:80]
    meta = r.get("pool_meta") if isinstance(r.get("pool_meta"), dict) else {}
    if meta.get("dex"): return str(meta.get("dex"))[:80]
    return None


def fields(r):
    """Denormalized columns from a research payload. Research JSON is stored separately."""
    m = r.get("metrics") or {}
    tok = r.get("token") or {}
    ws = r.get("wallet_score") or {}
    art = r.get("artificial_chart") or {}
    liq, fdv = _f(m.get("liq")), _f(m.get("fdv"))
    vol = _f(m.get("vol_h1"))
    authors, xtra = _x(r)
    gt = tok.get("gt_score_details")
    return {
        "liq": liq, "fdv": fdv,
        "liq_fdv": (liq / fdv) if liq is not None and fdv else None,
        "pool_age_min": _f(m.get("age_min")),
        "chain": r.get("network"),
        "dex": _dex(r),
        "launchpad": _launchpad(tok, r),
        "buyers_h1": _f(m.get("buyers_h1")),
        "sellers_h1": _f(m.get("sellers_h1")),
        "buys_h1": _f(m.get("buys_h1")),
        "sells_h1": _f(m.get("sells_h1")),
        "vol_h1": vol,
        "vol_liq": (vol / liq) if vol is not None and liq else None,
        "m5_change": _f(m.get("m5_change")),
        "h1_change": _f(m.get("h1_change")),
        "flow_buy_share": _f(r.get("flow_buy_share")),
        "top10_pct": _top10(r),
        "dev_pct": _f(tok.get("developer_holding_percentage")),
        "holder_count": _holders_count(tok),
        "gt_score": _f(tok.get("gt_score")),
        "gt_score_details": json.dumps(gt) if isinstance(gt, (dict, list)) else (None if gt is None else str(gt)[:500]),
        "is_honeypot": _boolish(tok.get("is_honeypot")),
        "is_nsfw": _boolish(tok.get("is_nsfw")),
        "human_score": _f(ws.get("human_participation")) if ws.get("human_participation") is not None else _f(r.get("human_score")),
        "human_source": ws.get("human_source") or r.get("human_score_source"),
        "artificial_score": _f(art.get("score")),
        "artificial_band": art.get("band"),
        "artificial_reasons": "; ".join(art.get("reasons") or [])[:500] or None,
        "x_authors": authors,
        "x_fields": json.dumps(xtra) if xtra else None,
    }


def _frozen(r):
    """Copy of the research payload without the live book scratch keys."""
    skip = {"_src", "_buzz", "_profile", "_verdict_source", "_early_label"}
    return {k: v for k, v in r.items() if k not in skip}


def _insert(c, row):
    ensure(c)
    cols = list(row)
    c.execute("insert into trade_features(" + ",".join(cols) + ") values(" + ",".join("?" * len(cols)) + ")", [row[k] for k in cols])
    return c.execute("select last_insert_rowid()").fetchone()[0]


def snapshot_trade(c, r, tier, verdict_source, why, buy_trade_id, entry_px=None):
    """Frozen features for one buy. Returns the new row id."""
    ensure(c)
    if buy_trade_id is not None and c.execute("select 1 from trade_features where buy_trade_id=?", (buy_trade_id,)).fetchone():
        return None
    import common as C
    data = fields(r)
    ref = entry_px if entry_px is not None else _f((r.get("metrics") or {}).get("price"))
    row = {
        "buy_trade_id": buy_trade_id, "ca": r.get("ca"), "network": r.get("network"), "pool": r.get("pool"),
        "symbol": (r.get("token") or {}).get("symbol"), "decided_at": C.now_iso(), "kind": "trade", "tier": tier,
        "verdict_source": verdict_source, "ai_verdict": r.get("ai_verdict"), "ai_reason": (r.get("ai_reason") or why or "")[:500],
        "early_verdict": r.get("prelim_verdict"), "research_json": json.dumps(_frozen(r), default=str),
        "entry_px": ref, "ref_px": ref, "ref_ts": C.now_iso(), "min_liq": data.get("liq"),
        **data,
    }
    return _insert(c, row)


def snapshot_skip(c, r, decision, why, verdict_source):
    """One outcome row for a token the AI book skipped or discarded. Not a trade."""
    ensure(c)
    ca, net = r.get("ca"), r.get("network")
    if ca and c.execute("select 1 from trade_features where ca=? and network=? and kind!='trade' and buy_trade_id is null", (ca, net)).fetchone():
        return None
    import common as C
    kind = "discard" if decision == "skip-hard" or "discard" in (why or "").lower() else "skip"
    data = fields(r)
    ref = _f((r.get("metrics") or {}).get("price"))
    row = {
        "buy_trade_id": None, "ca": ca, "network": net, "pool": r.get("pool"),
        "symbol": (r.get("token") or {}).get("symbol"), "decided_at": C.now_iso(), "kind": kind, "tier": None,
        "verdict_source": verdict_source, "ai_verdict": r.get("ai_verdict"), "ai_reason": (r.get("ai_reason") or why or "")[:500],
        "early_verdict": r.get("prelim_verdict"), "research_json": json.dumps(_frozen(r), default=str),
        "entry_px": ref, "ref_px": ref, "ref_ts": C.now_iso(),
        **data,
    }
    return _insert(c, row)


def _open_row(c, ca):
    ensure(c)
    return c.execute("select * from trade_features where ca=? and kind='trade' and exit_ts is null order by id desc limit 1", (ca,)).fetchone()


def update_hold(c, ca, entry_px, px, peak_px=None, trough_px=None, peak_at=None, opened_at=None, liq=None, now_iso=None):
    """Update max gain, max drawdown, time to peak, and liquidity path for an open trade."""
    row = _open_row(c, ca)
    if not row or not entry_px or not px or entry_px <= 0 or px <= 0: return
    import common as C
    now_iso = now_iso or C.now_iso()
    peak = max(peak_px or px, px, row["peak_px"] or 0)
    trough = min([x for x in (trough_px, px, row["trough_px"], entry_px) if x])
    gain = (peak / entry_px - 1) * 100
    dd = (trough / entry_px - 1) * 100
    ttp = row["time_to_peak_s"]
    if peak_at and opened_at and (row["peak_px"] or 0) < peak - 1e-15 * entry_px:
        try:
            ttp = D.datetime.fromisoformat(peak_at).timestamp() - D.datetime.fromisoformat(opened_at).timestamp()
        except Exception:
            ttp = row["time_to_peak_s"]
    elif (row["peak_px"] or 0) < peak and opened_at:
        try: ttp = D.datetime.fromisoformat(now_iso).timestamp() - D.datetime.fromisoformat(opened_at).timestamp()
        except Exception: pass
    min_liq = row["min_liq"]
    drop = row["liq_drop_pct"]
    events = []
    try: events = json.loads(row["liq_events"] or "[]")
    except Exception: events = []
    entry_liq = row["liq"]
    if liq is not None and liq >= 0:
        min_liq = liq if min_liq is None else min(min_liq, liq)
        if entry_liq:
            drop = (entry_liq - min_liq) / entry_liq * 100 if entry_liq else None
            crossed = drop is not None and drop >= 20 and (not events or events[-1].get("drop_pct", 0) < drop - 10)
            if crossed:
                events.append({"ts": now_iso, "liq": liq, "drop_pct": round(drop, 1)})
                events = events[-20:]
    c.execute("""update trade_features set max_gain_pct=?, max_drawdown_pct=?, time_to_peak_s=?, peak_px=?, trough_px=?,
                 min_liq=?, liq_drop_pct=?, liq_events=? where id=?""",
              (round(gain, 2), round(dd, 2), None if ttp is None else round(ttp, 1), peak, trough, min_liq,
               None if drop is None else round(drop, 2), json.dumps(events) if events else row["liq_events"], row["id"]))


def freeze_peak(c, plan):
    """Copy peak and trough off a risk plan onto the open feature row. Does not delete the plan."""
    if not plan: return
    ca = plan["ca"] if isinstance(plan, sqlite3.Row) or hasattr(plan, "keys") else plan.get("ca")
    row = _open_row(c, ca)
    if not row: return
    def g(k):
        try: return plan[k]
        except Exception: return None
    update_hold(c, ca, g("entry_px") or row["entry_px"], g("peak_px") or g("entry_px") or row["entry_px"],
                peak_px=g("peak_px"), trough_px=g("trough_px"), peak_at=g("peak_at"), opened_at=g("opened_at"))


def record_exit(c, ca, reason, kind=None, return_pct=None):
    """Store why the position closed. A liquidity write-off is -100%."""
    import common as C
    row = _open_row(c, ca)
    if not row: return
    text = (reason or kind or "")[:300]
    rug = (kind or "") == "rug" or "liquidity collapse" in text.lower() or "write-off" in text.lower()
    pct = -100.0 if rug else return_pct
    if pct is None:
        sell = c.execute("select realized_pnl, usd_notional from trades where ca=? and side='sell' order by id desc limit 1", (ca,)).fetchone()
        buy = c.execute("select usd_notional from trades where ca=? and side='buy' order by id desc limit 1", (ca,)).fetchone()
        if sell and buy and buy["usd_notional"]:
            pct = (sell["realized_pnl"] or 0) / buy["usd_notional"] * 100
    if rug:
        dd = -100.0 if row["max_drawdown_pct"] is None else min(row["max_drawdown_pct"], -100.0)
    else:
        dd = row["max_drawdown_pct"]
    c.execute("update trade_features set exit_reason=?, exit_ts=?, exit_return_pct=?, max_drawdown_pct=?, ref_px=coalesce(ref_px, entry_px), ref_ts=? where id=?",
              (text, C.now_iso(), None if pct is None else round(pct, 2), dd, C.now_iso(), row["id"]))


def note_ai(c, ca, verdict, reason, disagreed=False):
    row = _open_row(c, ca)
    if not row: return
    label = "AI disagreed" if disagreed else (verdict or "")
    if disagreed: label = "AI disagreed"
    c.execute("update trade_features set ai_later=?, ai_verdict=coalesce(?, ai_verdict), ai_reason=coalesce(ai_reason, ?) where id=?",
              (label[:200], verdict, (reason or "")[:500], row["id"]))


def _age_s(ts, now):
    if not ts: return None
    try: return now - D.datetime.fromisoformat(ts).timestamp()
    except Exception: return None


def follow_up(c=None, now=None, fetch=None, max_batch=30):
    """Fill px_1h / px_6h / px_24h for closed trades and for skips.

    Uses a cached price when one is already fresh. Otherwise one batched
    simple-price read per network, and only for rows whose next checkpoint
    is due. `max_batch` matches the CoinGecko API Demo (free) simple-price
    address cap. Rows left over wait for the next tracker pass.
    """
    import common as C
    own = c is None
    if c is None:
        path = os.path.join(C.BASE, "auto.db")
        if not os.path.exists(path): return 0
        c = sqlite3.connect(path, timeout=30); c.row_factory = sqlite3.Row
    ensure(c)
    now = time.time() if now is None else now
    horizons = ((1, "1h"), (6, "6h"), (24, "24h"))
    due = []
    for r in c.execute("select * from trade_features where px_24h is null").fetchall():
        anchor = r["exit_ts"] if r["kind"] == "trade" else (r["ref_ts"] or r["decided_at"])
        if r["kind"] == "trade" and not r["exit_ts"]: continue
        age = _age_s(anchor, now)
        if age is None: continue
        need = [col for h, col in horizons if age >= h * 3600 and r["px_" + col] is None]
        if need: due.append((r, need))
    if not due:
        if own: c.close()
        return 0
    by_net = {}
    for r, need in due:
        by_net.setdefault(r["network"] or "", []).append((r, need))
    n_upd = 0
    for net, items in by_net.items():
        chunk = items[:max_batch]
        prices = {}
        missing = []
        for r, _need in chunk:
            hit = None
            try:
                hit = C.last_price(C.mdb(), r["ca"], max_age=120)
            except Exception:
                hit = None
            if hit and hit[0]: prices[r["ca"]] = float(hit[0])
            else: missing.append(r["ca"])
        if missing and fetch is not False:
            fn = fetch or _fetch_prices
            try:
                got = fn(net, missing[:max_batch]) or {}
            except Exception:
                got = {}
            for ca, px in got.items():
                if px: prices[ca] = float(px)
        for r, need in chunk:
            px = prices.get(r["ca"])
            if not px: continue
            base = r["ref_px"] or r["entry_px"]
            sets = []
            vals = []
            for col in need:
                sets.append(f"px_{col}=?")
                vals.append(px)
                if base:
                    sets.append(f"ret_{col}=?")
                    vals.append(px / base - 1)
            vals.append(r["id"])
            c.execute("update trade_features set " + ",".join(sets) + " where id=?", vals)
            n_upd += 1
        if len(items) > max_batch:
            break
    c.commit()
    if own: c.close()
    return n_upd


def _fetch_prices(net, cas):
    """One simple-price call. Addresses the stream does not already cover."""
    if not net or not cas: return {}
    import common as C
    d = C.cg(f"/simple/networks/{net}/token_price/{','.join(cas)}", None, None) or {}
    attrs = ((d.get("data") or {}).get("attributes") or {}).get("token_prices") or {}
    out = {}
    for ca in cas:
        v = attrs.get(ca) or attrs.get(str(ca).lower())
        if v:
            try: out[ca] = float(v)
            except (TypeError, ValueError): pass
    return out
