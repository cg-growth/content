#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.client import CoinGeckoClient
from src.config import load_api_config


def main() -> None:
    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")

    print("[smoke] /ping")
    ping = client.request("/ping", snapshot_name="smoke_ping")
    print(ping)

    print("[smoke] /coins/markets for bitcoin")
    markets = client.request(
        "/coins/markets",
        params={"vs_currency": "usd", "ids": "bitcoin", "sparkline": "false"},
        snapshot_name="smoke_markets",
    )
    if not isinstance(markets, list) or not markets:
        raise RuntimeError("Unexpected /coins/markets payload in smoke test")

    print("[smoke] /coins/bitcoin minimal")
    coin = client.request(
        "/coins/bitcoin",
        params={
            "localization": "false",
            "tickers": "false",
            "market_data": "false",
            "community_data": "false",
            "developer_data": "false",
        },
        snapshot_name="smoke_coin_bitcoin",
    )
    if "image" not in coin:
        raise RuntimeError("Expected image object in /coins/{id} response")

    print("Smoke test completed.")


if __name__ == "__main__":
    main()
