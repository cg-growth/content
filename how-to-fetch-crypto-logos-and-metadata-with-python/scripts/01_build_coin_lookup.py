#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.client import CoinGeckoClient
from src.config import load_api_config
from src.io_utils import read_json, write_json

OUTPUT_LOOKUP = ROOT / "output" / "json" / "coins_lookup.json"
OUTPUT_DUPLICATES = ROOT / "output" / "json" / "coins_lookup_duplicates.json"
PREFERRED_SYMBOL_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "ripple",
    "ada": "cardano",
    "link": "chainlink",
    "doge": "dogecoin",
    "trx": "tron",
}


def build_coin_lookup(client: CoinGeckoClient, include_platform: bool = False) -> dict[str, str]:
    params = {"status": "active"}
    if include_platform:
        params["include_platform"] = "true"

    payload = client.request("/coins/list", params=params, snapshot_name="coins_list")
    lookup: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}

    symbol_candidates: dict[str, list[str]] = {}

    for coin in payload:
        symbol = (coin.get("symbol") or "").lower().strip()
        coin_id = coin.get("id")
        if not symbol or not coin_id:
            continue

        symbol_candidates.setdefault(symbol, []).append(coin_id)

        if symbol in lookup:
            duplicates.setdefault(symbol, [lookup[symbol]]).append(coin_id)
            continue

        lookup[symbol] = coin_id

    for symbol, preferred_id in PREFERRED_SYMBOL_IDS.items():
        candidates = symbol_candidates.get(symbol, [])
        if preferred_id in candidates:
            lookup[symbol] = preferred_id

    write_json(
        OUTPUT_LOOKUP,
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "/coins/list",
            "count": len(lookup),
            "lookup": lookup,
        },
    )
    write_json(OUTPUT_DUPLICATES, {"duplicates": duplicates, "count": len(duplicates)})
    return lookup


def get_coin_id(symbol: str, lookup: dict[str, str]) -> str | None:
    return lookup.get(symbol.lower().strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build local symbol->coin_id lookup map from /coins/list")
    parser.add_argument("--symbol", help="Optional symbol lookup test, e.g. btc")
    parser.add_argument(
        "--include-platform",
        action="store_true",
        help="Include contract address platforms in /coins/list payload",
    )
    args = parser.parse_args()

    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")

    lookup = build_coin_lookup(client, include_platform=args.include_platform)
    print(f"Lookup entries: {len(lookup)}")
    print(f"Saved: {OUTPUT_LOOKUP}")
    print(f"Duplicate symbols file: {OUTPUT_DUPLICATES}")

    if args.symbol:
        match = get_coin_id(args.symbol, lookup)
        print({"symbol": args.symbol, "coin_id": match})


if __name__ == "__main__":
    main()
