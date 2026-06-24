#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.client import CoinGeckoClient
from src.config import load_api_config
from src.extractors import flatten_markets_rows
from src.io_utils import chunked, write_csv, write_json
from src.watchlist_demo import render_watchlist_html


def _sort_rows_by_rank(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: row.get("market_cap_rank") or 10**9)


def get_bulk_logos_by_ids(
    client: CoinGeckoClient, coin_ids: list[str], pause_seconds: float = 2.0
) -> tuple[dict[str, str], list[dict]]:
    batches = chunked(coin_ids, 50)
    all_rows: list[dict] = []

    for index, batch in enumerate(batches, start=1):
        params = {
            "vs_currency": "usd",
            "ids": ",".join(batch),
            "per_page": min(len(batch), 50),
            "sparkline": "false",
        }
        payload = client.request("/coins/markets", params=params, snapshot_name=f"bulk_markets_batch_{index}")
        rows = flatten_markets_rows(payload)
        all_rows.extend(rows)

        if index < len(batches):
            time.sleep(pause_seconds)

    sorted_rows = _sort_rows_by_rank(all_rows)
    image_map = {row["id"]: row["image"] for row in sorted_rows if row.get("id") and row.get("image")}
    return image_map, sorted_rows


def get_bulk_logos_top_n(
    client: CoinGeckoClient, top_n: int, pause_seconds: float = 2.0
) -> tuple[dict[str, str], list[dict]]:
    if top_n < 1:
        raise ValueError("--top-n must be at least 1.")

    all_rows: list[dict] = []
    per_page = 250
    total_pages = (top_n + per_page - 1) // per_page

    for page in range(1, total_pages + 1):
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
        }
        payload = client.request("/coins/markets", params=params, snapshot_name=f"bulk_markets_top_page_{page}")
        rows = flatten_markets_rows(payload)
        all_rows.extend(rows)
        if page < total_pages:
            time.sleep(pause_seconds)

    sorted_rows = _sort_rows_by_rank(all_rows)[:top_n]
    image_map = {row["id"]: row["image"] for row in sorted_rows if row.get("id") and row.get("image")}
    return image_map, sorted_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk fetch coin image URLs from /coins/markets")
    parser.add_argument(
        "--coin-ids",
        default="",
        help="Optional comma-separated CoinGecko IDs (max 50 per request, chunked automatically)",
    )
    parser.add_argument("--top-n", type=int, default=20, help="Top N leaderboard coins by market cap (default mode)")
    parser.add_argument("--pause-seconds", type=float, default=2.0, help="Delay between batches")
    args = parser.parse_args()

    coin_ids = [item.strip() for item in args.coin_ids.split(",") if item.strip()]
    config = load_api_config()
    client = CoinGeckoClient(config, raw_output_dir=ROOT / "output" / "json" / "raw")

    if coin_ids:
        print("[info] Using explicit coin IDs mode. Rank numbers may contain gaps by design.")
        image_map, rows = get_bulk_logos_by_ids(client, coin_ids, pause_seconds=args.pause_seconds)
    else:
        print(f"[info] Using dynamic leaderboard mode: top {args.top_n} coins by market cap.")
        image_map, rows = get_bulk_logos_top_n(client, top_n=args.top_n, pause_seconds=args.pause_seconds)

    json_path = ROOT / "output" / "json" / "bulk_logos_map.json"
    csv_path = ROOT / "output" / "csv" / "bulk_logos_markets.csv"
    html_path = ROOT / "output" / "charts" / "watchlist_demo.html"

    write_json(json_path, image_map)
    write_csv(
        csv_path,
        rows,
        fieldnames=["id", "name", "symbol", "image", "current_price", "market_cap_rank"],
    )
    render_watchlist_html(rows, html_path)

    print(f"Saved image map: {json_path}")
    print(f"Saved markets CSV: {csv_path}")
    print(f"Saved frontend demo HTML: {html_path}")


if __name__ == "__main__":
    main()
