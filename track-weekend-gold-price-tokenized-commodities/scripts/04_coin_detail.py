import argparse
import json

from _http import CoinGeckoClient, prepare_output_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch selected detail fields for a CoinGecko coin ID.")
    parser.add_argument("--coin-id", default="pax-gold")
    parser.add_argument("--vs-currency", default="usd")
    parser.add_argument("--out-dir", default="output")
    return parser.parse_args()


def main():
    args = parse_args()
    client = CoinGeckoClient()
    output = prepare_output_dirs(args.out_dir)

    data = client.get_json(f"/coins/{args.coin_id}")

    summary = {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "asset_platform_id": data.get("asset_platform_id"),
        "price": data.get("market_data", {}).get("current_price", {}).get(args.vs_currency),
        "ath": data.get("market_data", {}).get("ath", {}).get(args.vs_currency),
        "total_volume": data.get("market_data", {}).get("total_volume", {}).get(args.vs_currency),
        "platforms": data.get("platforms", {}),
    }

    print(json.dumps(summary, indent=2))

    out_path = output["json"] / f"{args.coin_id}_detail_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
