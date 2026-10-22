"""Human-likeness from pool trades, and the choice between that and wallet labels.

Wallet labels (top traders, top holders, wallet PnL) are a measurement only when
some wallets are actually classified. An all-unknown set is not a score.

On every plan the scanner can also estimate human-likeness from
`/onchain/networks/{network}/pools/{pool}/trades` (recent pool trades).
Trades with is_anomalous=true are ignored. Below the minimum trade count the
estimate stays unknown (null), and the score drops that component instead of
inserting a placeholder.

Source labels stored on a trade:
  "wallet data"            — CoinGecko API Analyst plan or higher, real labels
  "trade-pattern estimate" — pattern estimate from pool trades
"""
import statistics
from datetime import datetime

SOURCE_WALLET = "wallet data"
SOURCE_PATTERN = "trade-pattern estimate"

DEFAULTS = {
    "min_trades": 12,
    "prior": 70.0,
    "unique_slope": 40.0,
    "top_share_high": 0.5,
    "top_share_high_penalty": 25.0,
    "top_share_mid": 0.35,
    "top_share_mid_penalty": 12.0,
    "size_cv_tight": 0.10,
    "size_cv_tight_penalty": 20.0,
    "size_cv_mid": 0.20,
    "size_cv_mid_penalty": 8.0,
    "round_share": 0.70,
    "round_penalty": 12.0,
    "same_second_share": 0.45,
    "same_second_penalty": 12.0,
    "clock_cv": 0.12,
    "clock_min_gaps": 8,
    "clock_penalty": 18.0,
    "size_liq_high": 0.08,
    "size_liq_dust": 0.00015,
    "size_liq_penalty": 10.0,
}


def cfg(over=None):
    out = dict(DEFAULTS)
    for k, v in (over or {}).items():
        if k.startswith("_") or v is None: continue
        out[k] = v
    return out


def _attrs(row):
    if isinstance(row, dict) and isinstance(row.get("attributes"), dict):
        return row["attributes"]
    return row if isinstance(row, dict) else {}


def anomalous(a):
    return a.get("is_anomalous") is True or a.get("is_anomaly") is True


def _ts(a):
    raw = a.get("block_timestamp") or a.get("timestamp")
    if raw is None: return None
    if isinstance(raw, (int, float)): return float(raw)
    try: return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
    except Exception: return None


def _usd(a):
    try: return float(a.get("volume_in_usd") or 0)
    except (TypeError, ValueError): return 0.0


def _roundish(x):
    if x <= 0: return False
    import math
    exp = math.floor(math.log10(x))
    base = x / (10 ** exp)
    for target in (1, 1.5, 2, 2.5, 5):
        if abs(base - target) / target <= 0.02: return True
    return False


def _cv(xs):
    if len(xs) < 3: return None
    mu = statistics.fmean(xs)
    if mu <= 0: return None
    return statistics.pstdev(xs) / mu


def usable(trades):
    """Non-anomalous trade attribute dicts, API order preserved."""
    out = []
    for row in trades or []:
        a = _attrs(row)
        if not a or anomalous(a): continue
        out.append(a)
    return out


def estimate(trades, liquidity=None, settings=None):
    """-> {human_participation|None, source, n, reasons, signals}.

    `trades` is the `data` array from pool trades, or a list of attribute dicts.
    """
    k = cfg(settings)
    rows = usable(trades)
    n = len(rows)
    base = {"human_participation": None, "source": None, "n": n, "reasons": [], "signals": {}}
    if n < int(k["min_trades"]):
        base["reasons"] = ["below minimum trades"]
        return base
    buys = [a for a in rows if (a.get("kind") or "").lower() == "buy"]
    addrs = [a.get("tx_from_address") or "" for a in (buys or rows)]
    addrs = [a for a in addrs if a]
    sample = buys or rows
    uniq = len(set(addrs))
    ratio = uniq / max(len(sample), 1)
    counts = {}
    for a in addrs:
        counts[a] = counts.get(a, 0) + 1
    top_share = (max(counts.values()) / len(addrs)) if counts else 0.0
    sizes = [x for x in (_usd(a) for a in rows) if x > 0]
    cv = _cv(sizes)
    round_share = (sum(1 for x in sizes if _roundish(x)) / len(sizes)) if sizes else 0.0
    stamps = [t for t in (_ts(a) for a in rows) if t is not None]
    stamps.sort()
    same_share = 0.0
    if stamps:
        buckets = {}
        for t in stamps:
            buckets[int(t)] = buckets.get(int(t), 0) + 1
        same_share = max(buckets.values()) / len(stamps)
    gaps = [stamps[i + 1] - stamps[i] for i in range(len(stamps) - 1) if stamps[i + 1] > stamps[i]]
    gap_cv = _cv(gaps) if len(gaps) >= int(k["clock_min_gaps"]) else None
    clock = gap_cv is not None and gap_cv <= float(k["clock_cv"])
    reasons = []
    score = float(k["prior"]) + (ratio - 0.5) * float(k["unique_slope"])
    if top_share >= float(k["top_share_high"]):
        score -= float(k["top_share_high_penalty"]); reasons.append("buys concentrated in few addresses")
    elif top_share >= float(k["top_share_mid"]):
        score -= float(k["top_share_mid_penalty"]); reasons.append("repeat buyers")
    if ratio < 0.35 and "buys concentrated in few addresses" not in reasons and "repeat buyers" not in reasons:
        reasons.append("few unique buyers vs total buys")
    if cv is not None and cv < float(k["size_cv_tight"]):
        score -= float(k["size_cv_tight_penalty"]); reasons.append("uniform trade sizes")
    elif cv is not None and cv < float(k["size_cv_mid"]):
        score -= float(k["size_cv_mid_penalty"]); reasons.append("similar trade sizes")
    if round_share >= float(k["round_share"]):
        score -= float(k["round_penalty"]); reasons.append("round trade sizes")
    if same_share >= float(k["same_second_share"]):
        score -= float(k["same_second_penalty"]); reasons.append("same-second trade bursts")
    if clock:
        score -= float(k["clock_penalty"]); reasons.append("clock-like timing")
    liq = None
    try:
        if liquidity is not None: liq = float(liquidity)
    except (TypeError, ValueError):
        liq = None
    if liq and liq > 0 and sizes:
        med = statistics.median(sizes)
        vs = med / liq
        if (vs >= float(k["size_liq_high"]) and top_share >= float(k["top_share_mid"])) or (vs <= float(k["size_liq_dust"]) and cv is not None and cv < float(k["size_cv_mid"])):
            score -= float(k["size_liq_penalty"]); reasons.append("trade size vs liquidity")
    score = round(max(0.0, min(100.0, score)), 1)
    return {
        "human_participation": score,
        "source": SOURCE_PATTERN,
        "n": n,
        "reasons": reasons,
        "signals": {
            "unique_buyer_ratio": round(ratio, 3),
            "top_address_share": round(top_share, 3),
            "size_cv": None if cv is None else round(cv, 3),
            "round_share": round(round_share, 3),
            "same_second_share": round(same_share, 3),
            "interval_cv": None if gap_cv is None else round(gap_cv, 3),
        },
    }


def fetch_trades(net, pool, mc=None):
    """GET /onchain/networks/{net}/pools/{pool}/trades. Returns the data array."""
    import common as C
    d = C.cg(f"/networks/{net}/pools/{pool}/trades", None, mc) or {}
    return d.get("data") or []


def from_pool(net, pool, liquidity=None, settings=None, mc=None, trades=None):
    """Estimate from pool trades. Fetches the endpoint when `trades` is not already in hand."""
    if trades is None:
        trades = fetch_trades(net, pool, mc)
    return estimate(trades, liquidity, settings)


def choose(wallet_score, pattern, wallets_on):
    """Pick the human score for this plan.

    Wallet data wins only on a CoinGecko API Analyst plan or higher, and only
    when it is a real measurement (not an all-unknown set). Otherwise the
    trade-pattern estimate is used when it cleared the minimum trade count.
    """
    ws = wallet_score or {}
    mix = ws.get("mix") or {}
    n = ws.get("n_wallets")
    if n is None: n = sum(mix.values()) if mix else 0
    unk = mix.get("unknown") or 0
    wallet_hp = ws.get("human_participation")
    real = bool(wallets_on) and wallet_hp is not None and n and unk < n
    if real:
        return wallet_hp, SOURCE_WALLET
    ph = (pattern or {}).get("human_participation")
    if ph is not None:
        return ph, SOURCE_PATTERN
    return None, None


def weighted(components, weights):
    """Renormalize `weights` over components that are present and not null.

    A missing human score is omitted. It is not filled with a placeholder.
    -> (score or None, used_weights)
    """
    comp = {}
    for k, v in (components or {}).items():
        if v is None: continue
        try: comp[k] = float(v)
        except (TypeError, ValueError): continue
    w = {}
    for k, v in (weights or {}).items():
        if k not in comp: continue
        try: w[k] = float(v)
        except (TypeError, ValueError): continue
    total = sum(w.values())
    if total <= 0 or not comp: return None, {}
    score = round(sum(comp[k] * wk for k, wk in w.items()) / total, 1)
    return score, {k: round(wk / total, 3) for k, wk in w.items()}
