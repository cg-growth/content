> Read the full article: [How To Know When Stablecoins Depeg (Real-Time Alerts)](https://www.coingecko.com/learn/how-to-know-when-stablecoins-depeg)

# Stablecoin Depeg Detection with the CoinGecko API

Companion code for the CoinGecko Learn guide on detecting stablecoin depegs in real time. It demonstrates three complementary data-delivery methods:

| Script | Method | What it does |
|--------|--------|--------------|
| `watchlist.py` | REST | Pulls a self-refreshing stablecoin watchlist (390+ coins) from the `stablecoins` category. |
| `poll_depeg.py` | REST polling | Polls `/simple/price` on an interval and flags any coin deviating from its $1.00 peg. |
| `stream_depeg.py` | WebSocket | Streams live prices via the `CGSimplePrice` channel and flags depegs as they happen. |
| `webhook_receiver.py` | Webhook | Verifies and handles `cg.coin.info.updated` events (e.g. public notices, reserve incidents). |

## Prerequisites

- **Python 3.9+**
- A **CoinGecko API key** — REST polling works on the free public API, while WebSocket streaming requires a paid plan (Basic and above). Get one from the [CoinGecko developer dashboard](https://www.coingecko.com/en/api/pricing).

## Installation

```bash
git clone https://github.com/cg-growth/content.git
cd content/how-to-know-when-stablecoins-depeg

# Install dependencies
pip install -r requirements.txt

# Set up your environment
cp .env.example .env
# Edit .env and add your COINGECKO_PRO_API_KEY (and CG_WEBHOOK_SECRET for the webhook receiver)
```

## Usage

### 1. Build a stablecoin watchlist (REST)

```bash
python watchlist.py
```

### 2. Poll for depegs (REST polling)

```bash
python poll_depeg.py
```

Adjust `THRESHOLD` (default `0.005` = 0.5%) and `INTERVAL` (default `30` seconds) at the top of the script.

### 3. Stream live prices (WebSocket)

Requires a paid-plan API key in `COINGECKO_PRO_API_KEY`.

```bash
export COINGECKO_PRO_API_KEY=your_pro_api_key_here
python stream_depeg.py
```

### 4. Receive webhook notices (Webhook)

```bash
export CG_WEBHOOK_SECRET=your_webhook_signing_secret_here
uvicorn webhook_receiver:app --port 8000
```

Configure the `cg.coin.info.updated` event to POST to `http://<your-host>:8000/cg-webhook` in the CoinGecko developer dashboard, and populate `WATCHLIST` with the stablecoin IDs you want to monitor.

## Endpoints used

- [`/coins/markets`](https://docs.coingecko.com/reference/coins-markets) — stablecoin watchlist
- [`/simple/price`](https://docs.coingecko.com/reference/simple-price) — REST polling
- [`CGSimplePrice`](https://docs.coingecko.com/websocket/cgsimpleprice) WebSocket channel — live streaming
- [`cg.coin.info.updated`](https://docs.coingecko.com/webhooks/cg-coin-info-updated) webhook event — metadata signals

## Links

- [CoinGecko API documentation](https://docs.coingecko.com)
- [CoinGecko API pricing](https://www.coingecko.com/en/api/pricing)
