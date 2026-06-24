import argparse
import sys

import pandas as pd

from config import USE_PRO_API
from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch OHLC range data (paid plans only).")
    parser.add_argument("--coin-id", default="pax-gold")
    parser.add_argument("--vs-currency", default="usd")
    parser.add_argument("--from", dest="from_ts", required=True, help="From timestamp/date (unix or ISO date).")
    parser.add_argument("--to", dest="to_ts", required=True, help="To timestamp/date (unix or ISO date).")
    parser.add_argument("--interval", choices=["daily", "hourly"], default="daily")
    parser.add_argument("--out-dir", default="output")
    return parser.parse_args()


def main():
    args = parse_args()

    if not USE_PRO_API:
        print("This script requires a paid CoinGecko API plan (Analyst+).")
        print("Set USE_PRO_API=true in .env and use a paid-plan API key to continue.")
        sys.exit(1)

    client = CoinGeckoClient()
    output = prepare_output_dirs(args.out_dir)

    params = {
        "vs_currency": args.vs_currency,
        "from": args.from_ts,
        "to": args.to_ts,
        "interval": args.interval,
    }

    data = client.get_json(f"/coins/{args.coin_id}/ohlc/range", params=params)

    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    csv_path = output["csv"] / f"{args.coin_id}_ohlc_range_{args.interval}.csv"
    df.to_csv(csv_path, index=False)

    print(f"Rows: {len(df)}")
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
