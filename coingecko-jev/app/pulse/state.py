from .window import PoolWindow, normalized_closes


def build_state(w: PoolWindow, now_ms: int, label: str) -> dict:
    now_sec = now_ms // 1000
    recent = [t for t in list(w.trades)[-10:]]
    state = {
        "pool": label,
        "features": w.features(now_ms),
        "last_60s_price_path_pct_from_start": normalized_closes(w.closes(now_sec, 60), 60),
        "last_10_trades_side_usd": [f"{'buy' if s == 'b' else 'sell'},{round(u)}" for _, s, u, _ in recent],
    }
    if w.wallet_flow:
        state["wallet_flow_last_5m"] = w.wallet_flow
    return state
