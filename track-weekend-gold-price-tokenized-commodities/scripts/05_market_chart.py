import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="Export market chart data and a line chart.")
    parser.add_argument("--coin-id", default="pax-gold")
    parser.add_argument("--vs-currency", default="usd")
    parser.add_argument("--days", default="30")
    parser.add_argument("--out-dir", default="output")
    return parser.parse_args()


def main():
    args = parse_args()
    client = CoinGeckoClient()
    output = prepare_output_dirs(args.out_dir)

    params = {"vs_currency": args.vs_currency, "days": args.days}
    data = client.get_json(f"/coins/{args.coin_id}/market_chart", params=params)

    prices_df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
    market_caps_df = pd.DataFrame(data["market_caps"], columns=["timestamp", "market_cap"])
    volumes_df = pd.DataFrame(data["total_volumes"], columns=["timestamp", "total_volume"])

    df = prices_df.merge(market_caps_df, on="timestamp", how="outer").merge(volumes_df, on="timestamp", how="outer")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.sort_values("timestamp")

    csv_path = output["csv"] / f"{args.coin_id}_market_chart_{args.days}d.csv"
    df.to_csv(csv_path, index=False)

    chart_path = output["charts"] / f"{args.coin_id}_market_chart_{args.days}d.png"
    plt.figure(figsize=(12, 5))
    plt.plot(df["timestamp"], df["price"])
    plt.title(f"{args.coin_id} market chart ({args.days} days)")
    plt.xlabel("Timestamp (UTC)")
    plt.ylabel(args.vs_currency.upper())
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(chart_path)

    print(f"Rows: {len(df)}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {chart_path}")


if __name__ == "__main__":
    main()
