import argparse

from _http import CoinGeckoClient


def parse_args():
    parser = argparse.ArgumentParser(description="List tokenized-related CoinGecko category IDs.")
    parser.add_argument("--contains", default="tokenized", help="Filter by substring in category_id/name.")
    return parser.parse_args()


def main():
    args = parse_args()
    client = CoinGeckoClient()
    categories = client.get_json("/coins/categories/list")

    needle = args.contains.lower()
    filtered = [
        item
        for item in categories
        if needle in item.get("category_id", "").lower() or needle in item.get("name", "").lower()
    ]

    print(f"Total categories: {len(categories)}")
    print(f"Matched ({args.contains}): {len(filtered)}")
    for item in filtered:
        print(f"- {item['category_id']}: {item['name']}")


if __name__ == "__main__":
    main()
