rename_map = {
    "c": "channel_type",
    "n": "network_id",
    "ta": "token_address",
    "p": "usd_price",
    "pp": "usd_price_24h_change_percentage",
    "m": "usd_market_cap",
    "v": "usd_24h_vol",
    "t": "last_updated_at",
}

async def stream_token_prices_and_write_to_pg(token_addresses):
    async with websockets.connect(WS_URL) as ws:
        # subscribe
        await ws.send(json.dumps({
            "command": "subscribe",
            "identifier": json.dumps({"channel": "OnchainSimpleTokenPrice"})
        }))

        # set tokens
        await ws.send(json.dumps({
            "command": "message",
            "identifier": json.dumps({"channel": "OnchainSimpleTokenPrice"}),
            "data": json.dumps({
                "network_id:token_addresses": [f"{NETWORK_ID}:{t}" for t in token_addresses],
                "action": "set_tokens"
            })
        }))

        while True:
            msg = await ws.recv()
            payload = json.loads(msg)

            # Debugging: print the raw payload
            # print(payload)

            if isinstance(payload, dict) and isinstance(payload.get("message"), dict):
                data = payload["message"]
            else:
                data = payload

            # Check if we get subscription confirmation
            if isinstance(data, dict) and data.get("code") == 2000:
                print(data.get("message"))

            # price data
            if isinstance(data, dict) and data.get("c") == "G1":
                row = {rename_map[k]: data.get(k) for k in rename_map}

                row["last_updated_at"] = (
                    pd.to_datetime(row["last_updated_at"], unit="s", utc=True)
                    .tz_convert("Europe/Berlin")
                )

                #print(row)

                cur.execute(
                    """
                    INSERT INTO price_stream
                    (channel_type, network_id, token_address, usd_price,
                     usd_price_24h_change_percentage, usd_market_cap, usd_24h_vol, last_updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["channel_type"],
                        row["network_id"],
                        row["token_address"],
                        row["usd_price"],
                        row["usd_price_24h_change_percentage"],
                        row["usd_market_cap"],
                        row["usd_24h_vol"],
                        row["last_updated_at"],
                    ),
                )
