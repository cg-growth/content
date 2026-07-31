def collect_pool_response(list_response):

    response = list_response.get("data", {})
    all_attributes = response.get("attributes", {})
    daily_tx = all_attributes["transactions"]["h24"]
    rel = response["relationships"]

    # Safely extract launchpad_details or default to empty dict
    launchpad_details = all_attributes.get("launchpad_details", {})

    response_dict = dict(
        pair = all_attributes["name"],
        dex = rel["dex"]["data"]["id"],
        token_add = rel["base_token"]["data"]["id"].split("_")[1],
        pool_add = all_attributes["address"],
        pool_created_at = all_attributes["pool_created_at"],
        fdv_usd = all_attributes["fdv_usd"],
        market_cap_usd = all_attributes["market_cap_usd"],
        daily_volume = all_attributes["volume_usd"]["h24"],
        daily_price_change = all_attributes["price_change_percentage"]["h24"],
        daily_buys = daily_tx["buys"],
        daily_sells = daily_tx["sells"],
        daily_buyers = daily_tx["buyers"],
        daily_sellers = daily_tx["sellers"],
        grad_pert = (
            launchpad_details.get("graduation_percentage")
            if launchpad_details else 0
        ),
        completed = launchpad_details.get("completed", False),
        completed_at = launchpad_details.get("completed_at", None),
        dest_pool = launchpad_details.get("migrated_destination_pool_address", None)
    )

    return response_dict
