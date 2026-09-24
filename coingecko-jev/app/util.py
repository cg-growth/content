from datetime import datetime, timezone


def f(x, default=None):
    if x is None or x == "":
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def rnd(x, n=2):
    return None if x is None else round(x, n)


def ratio(a, b, n=2):
    a, b = f(a), f(b)
    if a is None or not b:
        return None
    return round(a / b, n)


def short(addr: str | None) -> str:
    if not addr:
        return ""
    return addr if len(addr) <= 12 else f"{addr[:6]}…{addr[-4:]}"


def age_hours(iso: str | None):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1)
