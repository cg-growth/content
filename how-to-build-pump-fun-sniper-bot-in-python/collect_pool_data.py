def collect_pool_data(network, num_rows, max_pages):

    df_new_pools = get_new_pools(network, "pool_created_at", max_pages).head(num_rows)

    all_pool_data = []

    for pool_add in df_new_pools["pool_add"]:
        pool_data = get_pool_data(network, pool_add)
        all_pool_data.append(pool_data)

    df = pd.DataFrame(all_pool_data)

    df = df.astype({
        "pair": "string",
        "dex": "string",
        "pool_add": "string",
        "token_add": "string",
        "daily_buys": "Int64",
        "daily_sells": "Int64",
        "daily_buyers": "Int64",
        "daily_sellers": "Int64",
        "completed": "boolean",
        "dest_pool": "string",
    })

    # Numeric columns (coerce invalids to NaN)
    for col in ["fdv_usd", "market_cap_usd", "daily_volume", "daily_price_change", "grad_pert"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Timestamps
    df["pool_created_at"] = pd.to_datetime(df["pool_created_at"], utc=True, errors="coerce")
    df["completed_at"] = pd.to_datetime(df["completed_at"], utc=True, errors="coerce")

    return df
