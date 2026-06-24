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
from src.io_utils import write_csv, write_json


def get_trending(client: CoinGeckoClient, show_max: bool) -> list[dict]:
    params = {"show_max": "coins,nfts,categories"} if show_max else {}
    payload = client.request("/search/trending", params=params, snapshot_name="trending_search")

    rows: list[dict] = []
    for wrapper in payload.get("coins", []):
        item = wrapper.get("item", {})
        rows.append(
            {
                "id": item.get("id"),
                "coin_id": item.get("coin_id"),
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "thumb": item.get("thumb"),
                "small": item.get("small"),
                "large": item.get("large"),
                "market_cap_rank": item.get("market_cap_rank"),
                "score": item.get("score"),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch trending coins and their image fields")
    parser.add_argument(
        "--show-max",
        action="store_true",
        help="Request paid-plan extended result sets via show_max",
    )
    args = parser.parse_args()

    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")
    rows = get_trending(client, show_max=args.show_max)

    json_path = ROOT / "output" / "json" / "trending_coins.json"
    csv_path = ROOT / "output" / "csv" / "trending_coins.csv"

    write_json(json_path, rows)
    write_csv(
        csv_path,
        rows,
        fieldnames=["id", "coin_id", "name", "symbol", "thumb", "small", "large", "market_cap_rank", "score"],
    )

    print(f"Saved trending rows: {len(rows)}")
    print(f"Saved: {json_path}")
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
