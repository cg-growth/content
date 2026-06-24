import argparse
import json

import pandas as pd

from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch simple price for one or more CoinGecko IDs.")
    parser.add_argument("--ids", default="pax-gold,tether-gold")
    parser.add_argument("--vs-currency", default="usd")
    parser.add_argument("--out-dir", default="output")
    return parser.parse_args()


def main():
    args = parse_args()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()]

    client = CoinGeckoClient()
    output = prepare_output_dirs(args.out_dir)

    params = {
        "ids": ",".join(ids),
        "vs_currencies": args.vs_currency,
        "include_market_cap": "true",
        "include_24hr_change": "true",
    }

    data = client.get_json("/simple/price", params=params)
    print(json.dumps(data, indent=2))

    rows = []
    for coin_id in ids:
        item = data.get(coin_id, {})
        rows.append(
            {
                "id": coin_id,
                args.vs_currency: item.get(args.vs_currency),
                f"{args.vs_currency}_market_cap": item.get(f"{args.vs_currency}_market_cap"),
                f"{args.vs_currency}_24h_change": item.get(f"{args.vs_currency}_24h_change"),
            }
        )

    csv_path = output["csv"] / "simple_price.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
