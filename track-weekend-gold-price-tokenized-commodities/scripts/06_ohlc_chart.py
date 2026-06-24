import argparse

import pandas as pd
import plotly.graph_objects as go

from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="Export OHLC data and candlestick chart.")
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
    data = client.get_json(f"/coins/{args.coin_id}/ohlc", params=params)

    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    csv_path = output["csv"] / f"{args.coin_id}_ohlc_{args.days}d.csv"
    df.to_csv(csv_path, index=False)

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["timestamp"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=args.coin_id,
            )
        ]
    )
    fig.update_layout(
        title=f"{args.coin_id} OHLC ({args.days} days)",
        xaxis_title="Timestamp (UTC)",
        yaxis_title=args.vs_currency.upper(),
        template="plotly_white",
    )

    chart_path = output["charts"] / f"{args.coin_id}_ohlc_{args.days}d.html"
    fig.write_html(chart_path)

    print(f"Rows: {len(df)}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {chart_path}")


if __name__ == "__main__":
    main()
