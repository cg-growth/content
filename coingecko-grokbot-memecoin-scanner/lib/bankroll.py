"""One paper bankroll for both books: PAPER_START_CASH (default 10000).

A book with no trades adopts that amount when it is opened. A book that already
has trades is left unchanged, including its recorded start amount.
"""
import os, re
DEFAULT = 10000.0

def configured():
    """The bankroll the owner set. Missing or unusable values use the default."""
    raw = os.environ.get("PAPER_START_CASH", "")
    if raw is None or str(raw).strip() == "":
        return DEFAULT
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT
    if not (v > 0):
        return DEFAULT
    return v

def _trades(conn):
    try:
        return int(conn.execute("select count(*) from trades").fetchone()[0] or 0)
    except Exception:
        return None

def baseline(conn, fallback=None):
    """Start amount used for return math. A book with no trades uses the configured bankroll."""
    n = _trades(conn)
    if not n:
        return configured()
    try:
        row = conn.execute("select v from account where k='start_cash'").fetchone()
    except Exception:
        row = None
    if row is not None and row[0] is not None:
        return float(row[0])
    if fallback is not None:
        return float(fallback)
    return configured()

def _num(start):
    f = float(start)
    if f == int(f):
        return str(int(f))
    return format(f, "f").rstrip("0").rstrip(".")

def sync_policy(path, start):
    """Point auto/policy.json start_cash at the same bankroll. Other keys are left as they are."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return False
    m = re.search(r'("start_cash"\s*:\s*)(-?\d+(?:\.\d+)?)', text)
    if not m:
        return False
    if float(m.group(2)) == float(start):
        return False
    new = text[:m.start(2)] + _num(start) + text[m.end(2):]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.replace(tmp, path)
    return True

def apply(conn, sync_policy_path=None):
    """Adopt the configured bankroll when this book has no trades. Returns True if cash changed."""
    if _trades(conn):
        return False
    start = configured()
    try:
        cash = conn.execute("select v from account where k='cash'").fetchone()
    except Exception:
        return False
    try:
        base = conn.execute("select v from account where k='start_cash'").fetchone()
    except Exception:
        base = None
    changed = (cash is None or float(cash[0]) != float(start)
               or base is None or float(base[0]) != float(start))
    if changed:
        conn.execute("insert or replace into account(k,v) values('cash',?)", (start,))
        conn.execute("insert or replace into account(k,v) values('start_cash',?)", (start,))
        conn.commit()
    if sync_policy_path:
        sync_policy(sync_policy_path, start)
    return changed
