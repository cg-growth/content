def trade_status(usd_price, entry):

    if usd_price > entry * 1.5:
        return "take_profit"
    if usd_price < entry * 0.8:
        return "stop_loss"

    return "monitoring"

# Per-token state
state = {t: {"last_ts": None, "entry_price": None, "last_status": None} for t in token_list}

# Use ANSI escape codes in the print strings for colors
COLORS = {
    "monitoring": "\033[34m",  # blue
    "stop_loss": "\033[31m",   # red
    "take_profit": "\033[32m", # green
}
RESET = "\033[0m"

while True:
    time.sleep(2)

    for token in token_list:
        last_ts = state[token]["last_ts"]
        entry_price = state[token]["entry_price"]
        last_status = state[token]["last_status"]

        if last_ts is None:
            df = pd.read_sql(f"""
                                SELECT *,
                                    last_updated_at AT TIME ZONE 'Europe/Berlin' AS last_updated_at_cet
                                FROM price_stream
                                WHERE token_address = '{token}'
                                ORDER BY last_updated_at ASC
                            """, conn_r)
        else:
            df = pd.read_sql(f"""
                                SELECT *,
                                    last_updated_at AT TIME ZONE 'Europe/Berlin' AS last_updated_at_cet
                                FROM price_stream
                                WHERE token_address = '{token}'
                                  AND last_updated_at > '{last_ts}'
                                ORDER BY last_updated_at ASC
                            """, conn_r)

        if df.empty:
            continue

        if entry_price is None:
            entry_price = df.iloc[0]["usd_price"]

        for _, row in df.iterrows():
            status = trade_status(row["usd_price"], entry_price)

            ts = row["last_updated_at_cet"].strftime("%Y-%m-%d %H:%M:%S")
            price_fmt = f"{row['usd_price']:.8f}"
            entry_fmt = f"{entry_price:.8f}"
            pct = ((row["usd_price"] / entry_price) - 1) * 100

            if status != last_status:
                line = f"{ts} | {token[:12]}... | {status:<11} | price={price_fmt} | entry={entry_fmt} | chg={pct:>7.2f}%"
                print(f"{COLORS.get(status, '')}{line}{RESET}")
                last_status = status

            last_ts = row["last_updated_at"]

        state[token].update({"last_ts": last_ts, "entry_price": entry_price, "last_status": last_status})
