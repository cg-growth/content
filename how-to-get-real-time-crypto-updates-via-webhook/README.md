# How to Get Real-Time Crypto Updates Without Polling (Webhook Guide)

Companion code for the CoinGecko API Learn article:
[How to Get Real-Time Crypto Updates Without Polling (Webhook Guide)](https://www.coingecko.com/learn/how-to-get-real-time-crypto-updates-via-webhook).

Demonstrates a minimal Flask webhook receiver for CoinGecko's `cg.coin.info.updated` event: HMAC signature verification, replay protection, and idempotent event handling.

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies (`flask`, `python-dotenv`) |
| `.env.example` | Template env var (copy to `.env` and add your webhook signing secret) |
| `verify.py` | HMAC-SHA256 signature verification (constant-time compare) |
| `app.py` | Flask receiver: header checks, replay protection, signature verification, idempotency, dispatch |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env to add your webhook signing secret (whsec_...) from the Developer Dashboard
```

Get a free Demo API key: https://support.coingecko.com/hc/en-us/articles/21880397454233

## Run

```bash
ngrok http 8080      # expose a public HTTPS URL for local testing
python app.py        # start the Flask receiver on port 8080
```

Create the webhook in the [Developer Dashboard's Webhook section](https://www.coingecko.com/en/developers/dashboard#webhook), paste in your public URL, then click "Send Test Event" to validate the full integration.

## Endpoint used

- [`cg.coin.info.updated`](https://docs.coingecko.com/webhooks/cg-coin-info-updated) — fires whenever a tracked coin's metadata changes (categories, name/symbol, contract migrations, public notices, links)
