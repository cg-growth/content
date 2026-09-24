"""Deterministic mapping from Jev answers to chips, composite risk and presets."""

LOW_CONF = 0.5

CHIPS = [
    # (chip id, label, tone, test)
    ("organic", "Organic demand", "success", lambda a: _v(a, "demand") >= 67),
    ("artificial", "Artificial demand", "danger", lambda a: _v(a, "demand") <= 33),
    ("wash", "Wash-like", "danger", lambda a: _v(a, "wash_like") >= 0.7),
    ("whale", "Whale-heavy", "warning", lambda a: _v(a, "whale_heavy") >= 0.7),
    ("rug", "Rug risk", "danger", lambda a: _v(a, "rug_risk") >= 67),
    ("thin", "Thin liquidity", "warning", lambda a: _v(a, "thin_liq") >= 0.7),
    ("fresh", "Fresh launch", "info", lambda a: _v(a, "fresh") >= 0.7),
    ("sell", "Sell pressure", "danger", lambda a: _v(a, "sell_pressure") >= 67),
]

CONF_SOURCE = {"organic": "demand", "artificial": "demand", "rug": "rug_risk", "sell": "sell_pressure"}

COMPOSITE_FORMULA = "0.35·rug_risk + 0.20·(100 − demand) + 0.15·wash·100 + 0.15·whale·100 + 0.15·thin·100"


def _v(a: dict, qid: str) -> float:
    x = a.get(qid) or {}
    return x.get("value", 0.0) if x.get("type") != "choice" else 0.0


def chips(answers: dict) -> list[dict]:
    out = []
    for cid, label, tone, test in CHIPS:
        if test(answers):
            src = CONF_SOURCE.get(cid)
            conf = (answers.get(src) or {}).get("confidence") if src else None
            out.append({"id": cid, "label": label, "tone": tone, "low_conf": conf is not None and conf < LOW_CONF})
    return out


def composite(answers: dict) -> float:
    v = (
        0.35 * _v(answers, "rug_risk")
        + 0.20 * (100 - _v(answers, "demand"))
        + 0.15 * _v(answers, "wash_like") * 100
        + 0.15 * _v(answers, "whale_heavy") * 100
        + 0.15 * _v(answers, "thin_liq") * 100
    )
    return round(max(0.0, min(100.0, v)), 1)


def momentum(answers: dict) -> dict:
    m = answers.get("momentum") or {}
    conf = m.get("confidence")
    return {"value": m.get("choice"), "confidence": conf, "low_conf": conf is not None and conf < LOW_CONF}


def summarize(answers: dict) -> dict:
    return {"chips": chips(answers), "risk": composite(answers), "momentum": momentum(answers)}
