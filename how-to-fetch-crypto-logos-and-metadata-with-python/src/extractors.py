from __future__ import annotations

from typing import Any


class SchemaError(ValueError):
    pass


def _pick_first(values: list[Any] | None) -> str | None:
    if not values:
        return None
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_social_links(payload: dict[str, Any]) -> dict[str, str | None]:
    links = payload.get("links") or {}
    repos = links.get("repos_url") or {}
    return {
        "homepage": _pick_first(links.get("homepage")),
        "twitter_screen_name": links.get("twitter_screen_name"),
        "facebook_username": links.get("facebook_username"),
        "subreddit_url": links.get("subreddit_url"),
        "telegram_channel_identifier": links.get("telegram_channel_identifier"),
        "github_repo": _pick_first(repos.get("github")),
        "bitbucket_repo": _pick_first(repos.get("bitbucket")),
    }


def flatten_coin_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SchemaError("Expected dict payload for coin metadata.")

    image = payload.get("image")
    if not isinstance(image, dict):
        raise SchemaError("Expected payload.image to be an object.")

    required_image_keys = {"thumb", "small", "large"}
    missing = [key for key in required_image_keys if key not in image]
    if missing:
        raise SchemaError(f"Missing image keys: {missing}")

    description = payload.get("description") or {}

    result = {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "symbol": payload.get("symbol"),
        "description": description.get("en") if isinstance(description, dict) else None,
        "thumb_url": image.get("thumb"),
        "small_url": image.get("small"),
        "large_url": image.get("large"),
        "contract_addresses": payload.get("platforms") or {},
        "asset_platform_id": payload.get("asset_platform_id"),
        "genesis_date": payload.get("genesis_date"),
    }
    result.update(_extract_social_links(payload))
    return result


def flatten_markets_rows(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload:
        image = item.get("image")
        if image is None:
            raise SchemaError(f"Missing image in /coins/markets row for id={item.get('id')}")
        rows.append(
            {
                "id": item.get("id"),
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "image": image,
                "current_price": item.get("current_price"),
                "market_cap_rank": item.get("market_cap_rank"),
            }
        )
    return rows


def flatten_onchain_tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise SchemaError("Expected payload.data array for onchain token multi endpoint.")

    rows: list[dict[str, Any]] = []
    for item in data:
        attributes = item.get("attributes") or {}
        rows.append(
            {
                "id": item.get("id"),
                "address": attributes.get("address"),
                "name": attributes.get("name"),
                "symbol": attributes.get("symbol"),
                "image_url": attributes.get("image_url"),
                "coingecko_coin_id": attributes.get("coingecko_coin_id"),
                "price_usd": attributes.get("price_usd"),
            }
        )
    return rows


def flatten_onchain_tokens_from_included(payload: dict[str, Any]) -> list[dict[str, Any]]:
    included = payload.get("included")
    if not isinstance(included, list):
        raise SchemaError("Expected payload.included array for pool listing token includes.")

    dedup: dict[str, dict[str, Any]] = {}
    for item in included:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type not in {"token", "tokens"}:
            continue

        attributes = item.get("attributes") or {}
        token_id = item.get("id") or attributes.get("address")
        if not token_id:
            continue

        dedup[token_id] = {
            "id": item.get("id"),
            "address": attributes.get("address"),
            "name": attributes.get("name"),
            "symbol": attributes.get("symbol"),
            "image_url": attributes.get("image_url"),
            "coingecko_coin_id": attributes.get("coingecko_coin_id"),
            "price_usd": attributes.get("price_usd"),
        }

    return list(dedup.values())
