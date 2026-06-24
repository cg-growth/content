#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io_utils import ensure_dir, read_json


def download_coin_logo(coin_id: str, image_url: str, output_dir: Path, overwrite: bool = False) -> Path:
    ensure_dir(output_dir)
    out_path = output_dir / f"{coin_id}.png"
    if out_path.exists() and not overwrite:
        return out_path

    with requests.get(image_url, stream=True, timeout=20) as response:
        response.raise_for_status()
        with out_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download coin logo image and cache to local file")
    parser.add_argument("--coin-id", help="Coin ID for output filename")
    parser.add_argument("--image-url", help="Image URL to download")
    parser.add_argument(
        "--from-json",
        help="Path to JSON containing one metadata object with 'id' and preferred image URL field",
    )
    parser.add_argument(
        "--image-field",
        default="small_url",
        choices=["thumb_url", "small_url", "large_url", "image"],
        help="Field name to use when --from-json is provided",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite cached files")
    args = parser.parse_args()

    if args.from_json:
        payload = read_json(Path(args.from_json))
        coin_id = payload.get("id")
        image_url = payload.get(args.image_field)
    else:
        coin_id = args.coin_id
        image_url = args.image_url

    if not coin_id or not image_url:
        raise ValueError("Provide coin_id and image_url directly, or use --from-json with valid fields.")

    output_path = download_coin_logo(
        coin_id=coin_id,
        image_url=image_url,
        output_dir=ROOT / "output" / "logos",
        overwrite=args.overwrite,
    )
    print(f"Saved logo: {output_path}")


if __name__ == "__main__":
    main()
