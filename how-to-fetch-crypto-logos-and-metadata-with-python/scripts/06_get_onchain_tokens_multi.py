#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.client import CoinGeckoClient, NonRetryableRequestError
from src.config import load_api_config
from src.extractors import flatten_onchain_tokens, flatten_onchain_tokens_from_included
from src.io_utils import chunked, write_csv, write_json


def get_onchain_tokens_multi(client: CoinGeckoClient, network: str, addresses: list[str]) -> list[dict]:
    max_addresses = 50 if client.config.mode == "pro" else 30
    results: list[dict] = []

    for idx, batch in enumerate(chunked(addresses, max_addresses), start=1):
        endpoint = f"/onchain/networks/{network}/tokens/multi/{','.join(batch)}"
        payload = client.request(endpoint, params={"include_composition": "false"}, snapshot_name=f"onchain_multi_{idx}")
        results.extend(flatten_onchain_tokens(payload))

    return results


def get_onchain_recently_updated_tokens(client: CoinGeckoClient, network: str, limit: int) -> list[dict]:
    payload = client.request(
        "/onchain/tokens/info_recently_updated",
        params={"network": network},
        snapshot_name=f"onchain_recently_updated_{network}",
    )
    return flatten_onchain_tokens(payload)[:limit]


def get_onchain_tokens_from_pool_discovery(
    client: CoinGeckoClient,
    network: str,
    mode: str,
    limit: int,
    page: int,
) -> list[dict]:
    endpoint_map = {
        "trending-pools": f"/onchain/networks/{network}/trending_pools",
        "top-pools": f"/onchain/networks/{network}/pools",
        "new-pools": f"/onchain/networks/{network}/new_pools",
    }
    endpoint = endpoint_map[mode]

    params = {
        "include": "base_token,quote_token",
        "page": page,
    }
    payload = client.request(endpoint, params=params, snapshot_name=f"onchain_{mode}_{network}_page_{page}")
    rows = flatten_onchain_tokens_from_included(payload)
    return rows[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch onchain token metadata using address or discovery modes")
    parser.add_argument(
        "--mode",
        choices=["trending-pools", "top-pools", "new-pools", "recently-updated", "addresses"],
        default="trending-pools",
        help="Discovery mode for bulk on-chain token metadata (default: trending-pools)",
    )
    parser.add_argument("--network", default="eth", help="Onchain network ID, e.g. eth, solana, base")
    parser.add_argument(
        "--addresses",
        default="",
        help="Comma-separated token contract addresses (required only when --mode addresses)",
    )
    parser.add_argument("--limit", type=int, default=20, help="Max output tokens for discovery modes")
    parser.add_argument("--page", type=int, default=1, help="Page for pool discovery endpoints")
    args = parser.parse_args()

    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")
    try:
        if args.mode == "addresses":
            addresses = [item.strip() for item in args.addresses.split(",") if item.strip()]
            if not addresses:
                raise ValueError("Provide at least one --addresses value when --mode addresses is used.")
            rows = get_onchain_tokens_multi(client, args.network, addresses)
        elif args.mode == "recently-updated":
            rows = get_onchain_recently_updated_tokens(client, args.network, args.limit)
        else:
            rows = get_onchain_tokens_from_pool_discovery(
                client=client,
                network=args.network,
                mode=args.mode,
                limit=args.limit,
                page=args.page,
            )
    except NonRetryableRequestError as exc:
        message = str(exc)
        if "HTTP 401" in message:
            raise SystemExit(
                "Onchain endpoint requires an API key in this environment. "
                "Set COINGECKO_DEMO_API_KEY (or COINGECKO_PRO_API_KEY with CG_API_MODE=pro) and rerun."
            ) from exc
        raise

    mode_slug = args.mode.replace("-", "_")
    json_path = ROOT / "output" / "json" / f"onchain_tokens_{args.network}_{mode_slug}.json"
    csv_path = ROOT / "output" / "csv" / f"onchain_tokens_{args.network}_{mode_slug}.csv"

    write_json(json_path, rows)
    write_csv(
        csv_path,
        rows,
        fieldnames=["id", "address", "name", "symbol", "image_url", "coingecko_coin_id", "price_usd"],
    )

    print(f"Saved onchain rows: {len(rows)} (mode={args.mode}, network={args.network})")
    print(f"Saved: {json_path}")
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
