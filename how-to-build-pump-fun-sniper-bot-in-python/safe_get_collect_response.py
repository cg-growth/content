def safe_get(d, path, default=None):
    """Safely get a nested dictionary value."""
    for key in path:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d

def collect_response(list_response):

    response_all = []

    for response in list_response.get("data", []):

        all_attributes = response.get("attributes", {})
        rel = response.get("relationships", {})

        base_token_add = safe_get(rel, ["base_token", "data", "id"], "NA")

        # If token_add exists, split it.
        token_add = base_token_add.split("_")[1] if base_token_add != "NA" and "_" in base_token_add else "NA"

        temp_dict = dict(
            pair = safe_get(all_attributes, ["name"], "NA"),
            pool_created_at = safe_get(all_attributes, ["pool_created_at"], "NA"),
            dex = safe_get(rel, ["dex", "data", "id"], "NA"),
            network = safe_get(rel, ["network", "data", "id"], "NA"),
            token_add = token_add,
            pool_add = safe_get(all_attributes, ["address"], "NA"),
            fdv_usd = safe_get(all_attributes, ["fdv_usd"], "NA"),
            market_cap_usd = safe_get(all_attributes, ["market_cap_usd"], "NA"),
            daily_volume = safe_get(all_attributes, ["volume_usd", "h24"], "NA"),
            daily_price_change = safe_get(all_attributes, ["price_change_percentage", "h24"], "NA"),
        )

        response_all.append(temp_dict)

    return response_all
