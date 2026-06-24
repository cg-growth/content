def format_exit_message(symbol: str, pnl_pct: float, tp_threshold: float) -> str:
    """Format exit event message based on TP or SL trigger"""
    is_tp = pnl_pct >= tp_threshold
    event_type = "TAKE PROFIT" if is_tp else "STOP LOSS"
    emoji = "🎯" if is_tp else "🛑"
    return f"{emoji} {event_type} HIT for {symbol}!"
