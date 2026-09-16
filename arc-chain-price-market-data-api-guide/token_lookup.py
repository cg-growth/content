import os
from coingecko_sdk import Coingecko

client = Coingecko(
    demo_api_key=os.environ["COINGECKO_DEMO_API_KEY"],
    environment="demo",
)

def lookup_token(asset_platform_id: str, network_id: str, contract_address: str) -> None:
    """Look up a token by contract address across CoinGecko and GeckoTerminal."""

    # Step 1: try CoinGecko's curated database first
    try:
        coin = client.coins.contract.get(contract_address, id=asset_platform_id)
        coingecko_id = coin.id
        print(f"Listed on CoinGecko as '{coingecko_id}' ({coin.name})")
    except Exception:
        coingecko_id = None
        print("Not yet listed on CoinGecko's curated database.")

    # Step 2: always check GeckoTerminal, which indexes independently and faster
    onchain_info = client.onchain.networks.tokens.info.get(
        contract_address, network=network_id
    )
    token_attrs = onchain_info.data.attributes
    print(f"Onchain as '{token_attrs.symbol}': GT Score {token_attrs.gt_score:.1f}, "
          f"honeypot status: {token_attrs.is_honeypot}")

    # Step 3: current price and market cap
    if coingecko_id:
        price = client.simple.token_price.get_id(
            asset_platform_id,
            contract_addresses=contract_address,
            vs_currencies="usd",
            include_market_cap=True,
        )
        print("Price (CoinGecko):", price)
    else:
        onchain_price = client.onchain.simple.networks.token_price.get_addresses(
            contract_address, network=network_id, include_market_cap=True,
            mcap_fdv_fallback=True,
        )
        print("Price (GeckoTerminal, FDV fallback):", onchain_price.data.attributes.token_prices)

    # Step 4: historical data, only if listed on CoinGecko
    if coingecko_id:
        history = client.coins.contract.market_chart.get(
            contract_address, id=asset_platform_id, vs_currency="usd", days="7",
        )
        print(f"{len(history.prices)} historical price points over the last 7 days")

    # Step 5: pools and liquidity
    pools = client.onchain.networks.tokens.pools.get(
        contract_address, network=network_id, include="base_token,quote_token",
    )
    for pool in pools.data[:3]:
        print(f"Pool: {pool.attributes.name}: ${float(pool.attributes.reserve_in_usd):,.0f} liquidity")

if __name__ == "__main__":
    # Circle Wrapped BTC (cirBTC) on Arc Chain — Circle's institutional
    # wrapped-BTC asset, live on Arc since launch.
    lookup_token(
        asset_platform_id="arc",
        network_id="arc",
        contract_address="0x171a4217b86a807a64eb94757db6849fb4bdbaa0",
    )
