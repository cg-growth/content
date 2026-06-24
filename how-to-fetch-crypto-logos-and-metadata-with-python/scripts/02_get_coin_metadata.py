#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.client import CoinGeckoClient
from src.config import load_api_config
from src.extractors import flatten_coin_metadata
from src.io_utils import write_json


def get_coin_metadata(client: CoinGeckoClient, coin_id: str) -> dict:
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "false",
        "community_data": "false",
        "developer_data": "false",
    }
    payload = client.request(f"/coins/{coin_id}", params=params, snapshot_name=f"coin_{coin_id}")
    return flatten_coin_metadata(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch single coin metadata with thumb/small/large logo URLs")
    parser.add_argument("--coin-id", default="bitcoin", help="CoinGecko coin ID, e.g. bitcoin")
    args = parser.parse_args()

    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")

    result = get_coin_metadata(client, args.coin_id)
    output_path = ROOT / "output" / "json" / f"coin_metadata_{args.coin_id}.json"
    write_json(output_path, result)

    print(f"Saved: {output_path}")
    print(result)


if __name__ == "__main__":
    main()
