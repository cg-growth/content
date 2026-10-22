"""Trade-tape helpers. Anomalous trades stay out of buyer and flow counts.

CoinGecko trades endpoints exclude anomalous trades unless include_anomalous=true.
This scanner does not opt in. When a trade still carries is_anomalous, it is ignored
so it cannot count as a human buyer or as buy/sell flow.
"""

def is_anomalous(attrs):
    """True when the trade is flagged anomalous. Missing field means not flagged."""
    if not isinstance(attrs, dict): return False
    v = attrs.get("is_anomalous")
    if isinstance(v, str): return v.strip().lower() in ("true", "1", "yes")
    return v is True or v == 1


def accumulate(rows, net, norm):
    """Oldest-or-given order. rows are CoinGecko trade objects or attribute dicts.
    -> (wallets by address, skipped_anomalous_count)."""
    ws = {}
    skipped = 0
    for x in rows or []:
        a = x.get("attributes") if isinstance(x, dict) and "attributes" in x else (x if isinstance(x, dict) else {})
        if not a: continue
        if is_anomalous(a):
            skipped += 1
            continue
        kind = a.get("kind") or ""
        vol = a.get("volume_in_usd")
        try: usd = float(vol or 0)
        except (TypeError, ValueError): usd = 0.0
        w = norm(a.get("tx_from_address") or "", net)
        if not w: continue
        e = ws.setdefault(w, {"address": w, "buy": 0.0, "sell": 0.0, "block": a.get("block_number"), "first_seen": a.get("block_timestamp")})
        if kind == "buy": e["buy"] += usd
        elif kind == "sell": e["sell"] += usd
    return ws, skipped
