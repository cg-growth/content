import argparse

import pandas as pd

from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="List market data for a CoinGecko category.")
    parser.add_argument("--category", default="tokenized-gold")
    parser.add_argument("--vs-currency", default="usd")
    parser.add_argument("--order", default="market_cap_desc")
    parser.add_argument("--per-page", type=int, default=20)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--out-dir", default="output")
    return parser.parse_args()


def main():
    args = parse_args()
    client = CoinGeckoClient()
    output = prepare_output_dirs(args.out_dir)

    params = {
        "vs_currency": args.vs_currency,
        "category": args.category,
        "order": args.order,
        "per_page": args.per_page,
        "page": args.page,
    }
    data = client.get_json("/coins/markets", params=params)

    columns = [
        "id",
        "name",
        "symbol",
        "current_price",
        "market_cap",
        "total_volume",
        "price_change_percentage_24h",
    ]
    df = pd.DataFrame(data)
    if df.empty:
        print("No rows returned.")
        return

    df = df[columns]
    print(df.to_string(index=False))

    csv_path = output["csv"] / f"markets_{args.category}.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
