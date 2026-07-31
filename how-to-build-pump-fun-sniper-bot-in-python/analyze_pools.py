def analyze_pools(network, num_rows, max_pages=5):

    df_pool_data = collect_pool_data(network, num_rows, max_pages)

    # Inspect key metrics such as Fully Diluted Volume (FDV) and age of the pool. We want
    # to filter out pools which are older than 10 minutes and have FDV less than $5000.
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=10)

    df_filtered = df_pool_data[
                        (df_pool_data["pool_created_at"] >= cutoff) &
                        (df_pool_data["fdv_usd"] > 2500) &
                        (df_pool_data["grad_pert"] < 75)
                        ].copy()

    # Convert to local timezone
    df_filtered["pool_created_at"] = df_filtered["pool_created_at"].dt.tz_convert("Europe/Berlin")

    return df_filtered.sort_values(by = "grad_pert", ascending = False)
