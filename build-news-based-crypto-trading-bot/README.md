> Read the full article: [How to Build a News-Based Crypto Trading Bot in Python](https://www.coingecko.com/learn/build-news-based-crypto-trading-bot)

# CoinGecko News-Based Crypto Trading Bot (Python)

A Python starter bot that reads real-time crypto news, scores each headline with an LLM, confirms the signal against live CoinGecko market data, and records simulated (paper) trades locally -- including a simple exit rule to close positions on a reversing signal.

## What You Can Do

- Fetch real-time crypto news via CoinGecko's Crypto News endpoint
- Score headline sentiment and confidence with an LLM (Claude, swappable for any structured-output LLM)
- Confirm a signal against live price data before sizing a trade
- Simulate buys and sells in a local paper-trading portfolio, with fees and slippage applied on both sides
- Track realized and unrealized PnL with a single bulk `/simple/price` call
- Exit a position on a sufficiently bearish, price-confirmed reversal (a simplified illustration, not a production strategy)
- Report which filter is rejecting the most signals, to help tune thresholds

## Quick Start

```bash
git clone https://github.com/cg-growth/content.git
cd content/build-news-based-crypto-trading-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env
```

Set your API keys in `.env`:

```ini
COINGECKO_API_KEY=CG-your_api_key_here
COINGECKO_PLAN=analyst
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

The Crypto News endpoint (`/news`) used by `fetch_news.py` and `bot.py` requires the Analyst plan or above. `confirm_signal.py`, `paper_trader.py`, and `false_signal_report.py` run standalone with no API key at all.

## Scripts

```bash
python fetch_news.py           # Fetch the latest crypto news headlines
python score_news.py           # Score sample headlines for sentiment + confidence
python confirm_signal.py       # Demo: entry and exit gate logic against sample price data
python bot.py                  # Full pipeline: news -> score -> confirm -> paper trade -> exit
python false_signal_report.py  # Breakdown of which filter rejects the most signals
```

`paper_trader.py` has no `__main__` entry point -- it's imported by `bot.py`, which is where `PaperPortfolio` gets used.

## Files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies (`requests`, `pandas`, `anthropic`, `python-dotenv`) |
| `example.env` | Template env vars (copy to `.env` and add your API keys) |
| `config.py` | Plan-based API host/header switching, plus all strategy thresholds |
| `fetch_news.py` | Fetch the latest crypto news articles |
| `score_news.py` | Score a headline's sentiment and confidence with an LLM |
| `confirm_signal.py` | Entry gate (`should_trade`) and exit gate (`should_exit`) against live price data |
| `paper_trader.py` | Local SQLite paper-trading portfolio: buy, sell, cooldown, signal log |
| `bot.py` | Full pipeline: fetch, resolve the tradeable coin, score, confirm/exit, trade, track PnL |
| `false_signal_report.py` | Breakdown of which filter is rejecting the most signals |

## Endpoints used

- [`/news`](https://docs.coingecko.com/reference/news) -- Latest crypto news articles (Analyst plan and above)
- [`/coins/markets`](https://docs.coingecko.com/reference/coins-markets) -- Market cap, volume, and price change for the coin(s) mentioned in a headline
- [`/simple/price`](https://docs.coingecko.com/reference/simple-price) -- Bulk price lookup (up to 515 IDs per request) for realized/unrealized PnL

## Disclaimer

All trades in this project are paper trades -- no exchange keys or real orders are involved. This is for educational purposes only and does not constitute financial advice. All trading involves risk. Do your own research before making any investment decisions. The exit rule in `confirm_signal.py` (`should_exit`) is intentionally simple and is not a recommended production strategy; test and refine it before relying on any variation of it with real capital.
