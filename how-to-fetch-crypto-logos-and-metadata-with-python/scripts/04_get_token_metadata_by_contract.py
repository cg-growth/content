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


def get_token_metadata_by_contract(client: CoinGeckoClient, platform: str, contract_address: str) -> dict:
    endpoint = f"/coins/{platform}/contract/{contract_address}"
    payload = client.request(endpoint, snapshot_name=f"contract_{platform}_{contract_address[:10]}")
    return flatten_coin_metadata(payload)

def list_asset_platforms(client: CoinGeckoClient) -> list[dict]:
    payload = client.request("/asset_platforms", snapshot_name="asset_platforms")
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected /asset_platforms payload type.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch token metadata and logos by asset platform + contract address")
    parser.add_argument("--platform", default="ethereum", help="Asset platform ID, e.g. ethereum")
    parser.add_argument(
        "--contract-address",
        default="0x514910771af9ca656af840dff83e8264ecf986ca",
        help="Token contract address",
    )
    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="Print top asset platforms from /asset_platforms and exit",
    )
    args = parser.parse_args()

    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")

    if args.list_platforms:
        platforms = list_asset_platforms(client)
        for item in platforms[:20]:
            print({"id": item.get("id"), "name": item.get("name")})
        print(f"Total platforms: {len(platforms)}")
        return

    result = get_token_metadata_by_contract(client, args.platform, args.contract_address)
    output_path = ROOT / "output" / "json" / f"contract_metadata_{args.platform}_{args.contract_address[:10]}.json"
    write_json(output_path, result)

    print(f"Saved: {output_path}")
    print(result)


if __name__ == "__main__":
    main()
