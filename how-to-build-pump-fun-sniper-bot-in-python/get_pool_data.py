def get_pool_data(network, pool_address):

    target_url = f"/onchain/networks/{network}/pools/{pool_address}"

    pool_list_response = get_response(target_url,
                                      use_pro,
                                      "",
                                      PRO_URL)
    # SDK equivalent: client.onchain.networks.pools.get_address(pool_address, network=network)

    pool_all = collect_pool_response(pool_list_response)

    return pool_all
