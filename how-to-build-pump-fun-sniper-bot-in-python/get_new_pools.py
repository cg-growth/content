def get_new_pools(network, sort_by_col, max_pages=None):

    endpoint = f"/onchain/networks/{network}/new_pools"
    params = {}
    newpools_all = []
    page_count = 0

    # Follow pagination via the response links.next and collect across pages, with an optional max_pages cap.
    while True:
        pools_list_response = get_response(endpoint, use_pro, params, PRO_URL)

        # Prefer less setup? Equivalent call using CoinGecko's official Python SDK:
        # pip install coingecko-sdk
        #
        # from coingecko_sdk import Coingecko
        # client = Coingecko(pro_api_key=CG_PRO_API_KEY, environment="pro")
        #
        # response = client.onchain.networks.new_pools.get_network(network, page=page_count + 1)
        # pools_list_response = response.model_dump()

        if not pools_list_response:
            break

        newpools_all.extend(collect_response(pools_list_response))
        page_count += 1

        if max_pages is not None and page_count >= max_pages:
            break

        links = pools_list_response.get("links", {})
        next_link = links.get("next") if isinstance(links, dict) else None
        if not next_link:
            break

        parsed = urlparse(next_link)
        endpoint = parsed.path
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    df_new_pools = pd.DataFrame(newpools_all)

    # Change to local timezone
    df_new_pools["pool_created_at"] = pd.to_datetime(df_new_pools["pool_created_at"], utc=True)
    df_new_pools["pool_created_at"] = df_new_pools["pool_created_at"].dt.tz_convert("Europe/Berlin")

    return df_new_pools[df_new_pools["dex"] == "pump-fun"].sort_values(
        by=[f"{sort_by_col}"], ascending=False
    )
