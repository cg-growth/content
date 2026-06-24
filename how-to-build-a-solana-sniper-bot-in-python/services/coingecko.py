import asyncio
from dataclass_wizard import fromdict
import requests
import json
import websockets
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from models import pool
from utils.load_env import cg_api_key
from models.pool import Pool, Pools


class CoinGecko:
    BASE_URL = "https://pro-api.coingecko.com/api/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key or cg_api_key
        self.headers = {"accept": "application/json"}
        if self.api_key:
            self.headers["x-cg-pro-api-key"] = self.api_key

    def get_new_pools(self, num_pages: int = 1) -> Pools:
        url = f"{self.BASE_URL}/onchain/networks/solana/new_pools"
        all_pools = []
        for page in range(1, num_pages + 1):
            response = requests.get(
                url, headers=self.headers, params={"page": page}, timeout=30
            )
            pools = fromdict(Pools, response.json())
            all_pools.extend(pools.data)
        return Pools(data=all_pools)

    def filter_pools(
        self,
        pools: Pools,
        min_pool_age_minutes: int,
        max_pool_age_minutes: int,
        min_liquidity_usd: float,
        min_volume_usd: float = 0,
    ) -> List[Pool]:
        result = []

        for pool in pools.data:
            if not pool.attributes:
                continue

            age = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(
                    pool.attributes.pool_created_at.replace("Z", "+00:00")
                )
            ).total_seconds() / 60
            liquidity = float(pool.attributes.reserve_in_usd or 0)
            volume = float(pool.attributes.volume_usd.h24 or 0)

            if min_pool_age_minutes > age or age > max_pool_age_minutes:
                continue
            if liquidity < min_liquidity_usd:
                continue
            if min_volume_usd and volume < min_volume_usd:
                continue
            result.append(pool)
        return result

    async def stream_token_prices(
        self,
        tokens: List[str],
        subscribed_tokens: set = None,
        data_manager=None,
        get_monitored_tokens_func=None,
    ):
        """Stream token prices. Yields price data or 'reconnect' signal."""
        ws_url = f"wss://stream.coingecko.com/v1?x_cg_pro_api_key={self.api_key}"
        channel = '{"channel":"OnchainSimpleTokenPrice"}'

        try:
            async with websockets.connect(
                ws_url, ping_interval=20, ping_timeout=10
            ) as ws:
                # Subscribe to channel
                subscribe_msg = {
                    "command": "subscribe",
                    "identifier": channel,
                }
                await ws.send(json.dumps(subscribe_msg))

                # Set tokens to stream - tokens should be like "solana:0x..."
                set_token_msg = {
                    "command": "message",
                    "identifier": channel,
                    "data": json.dumps(
                        {
                            "network_id:token_addresses": tokens,
                            "action": "set_tokens",
                        }
                    ),
                }
                await ws.send(json.dumps(set_token_msg))

                # Stream prices
                while True:
                    try:
                        message = json.loads(
                            await asyncio.wait_for(ws.recv(), timeout=10.0)
                        )
                    except asyncio.TimeoutError:
                        # Check if token list changed during timeout
                        if (
                            subscribed_tokens
                            and data_manager
                            and get_monitored_tokens_func
                        ):
                            current_tokens = set(
                                get_monitored_tokens_func(data_manager)
                            )
                            if current_tokens != subscribed_tokens:
                                yield {"_reconnect": True}
                                return
                        continue

                    if message.get("p"):  # Has price data
                        yield {
                            "token": f"{message.get('n')}:{message.get('ta')}",
                            "price": message.get("p"),
                            "change_24h": message.get("pp"),
                            "market_cap": message.get("m"),
                            "volume_24h": message.get("v"),
                        }

        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
            websockets.exceptions.WebSocketException,
        ) as e:
            print(f"⚠️ Websocket disconnected: {e}. Reconnecting...")

        except GeneratorExit:
            # Generator was closed by consumer, clean exit
            pass

        except Exception as e:
            print(f"❌ Unexpected error in price stream: {e}")
