import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a weekend movement view from tokenized commodity prices.")
    parser.add_argument("--coin-id", default="pax-gold")
    parser.add_argument("--vs-currency", default="usd")
    parser.add_argument("--days", default="30")
    parser.add_argument("--input-csv", default=None, help="Optional market chart CSV with timestamp and price columns.")
    parser.add_argument("--out-dir", default="output")
    return parser.parse_args()


def load_price_data(args, client: CoinGeckoClient) -> pd.DataFrame:
    if args.input_csv:
        df = pd.read_csv(args.input_csv)
        if "timestamp" not in df.columns or "price" not in df.columns:
            raise ValueError("Input CSV must contain timestamp and price columns.")
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.sort_values("timestamp").reset_index(drop=True)

    params = {"vs_currency": args.vs_currency, "days": args.days}
    data = client.get_json(f"/coins/{args.coin_id}/market_chart", params=params)

    prices = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms", utc=True)
    return prices.sort_values("timestamp").reset_index(drop=True)


def main():
    args = parse_args()
    client = CoinGeckoClient()
    output = prepare_output_dirs(args.out_dir)

    df = load_price_data(args, client).set_index("timestamp")
    weekend_df = df[df.index.dayofweek >= 5].copy()

    if weekend_df.empty:
        raise RuntimeError("No weekend rows found. Increase --days and try again.")

    weekend_csv = output["csv"] / f"{args.coin_id}_weekend_only_{args.days}d.csv"
    weekend_df.reset_index().to_csv(weekend_csv, index=False)

    chart_path = output["charts"] / f"{args.coin_id}_weekend_gap_{args.days}d.png"
    plt.figure(figsize=(12, 5))
    plt.plot(df.index, df["price"], label="All days", alpha=0.7)
    plt.scatter(weekend_df.index, weekend_df["price"], color="red", s=12, label="Weekend points")
    plt.title(f"{args.coin_id} weekend movement ({args.days} days)")
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel(args.vs_currency.upper())
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(chart_path)

    print(f"Total points: {len(df)}")
    print(f"Weekend points: {len(weekend_df)}")
    print(f"Saved: {weekend_csv}")
    print(f"Saved: {chart_path}")


if __name__ == "__main__":
    main()
