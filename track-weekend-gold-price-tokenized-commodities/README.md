> Read the full article: [How to Track Gold, Silver & Tokenized Commodities 24/7 Including Weekends](https://www.coingecko.com/learn/track-weekend-gold-price-tokenized-commodities)

# CoinGecko Tokenized Commodities Python Toolkit

A clean Python starter repository for tracking tokenized commodities like PAX Gold (`pax-gold`) and Tether Gold (`tether-gold`) with CoinGecko API.

This version is streamlined for readers:
- simple scripts
- clean outputs
- minimal setup

## What You Can Do

- Discover tokenized commodity categories
- List tokens in `tokenized-gold`, `tokenized-silver`, and `tokenized-commodities`
- Fetch real-time prices for PAXG and XAUT
- Pull detailed metadata for a token
- Export market chart and OHLC data
- Generate a weekend movement view
- Use paid-plan OHLC range when available

## Quick Start

```bash
git clone https://github.com/cg-brianlsh/coingecko-tokenized-commodities-python.git
cd coingecko-tokenized-commodities-python
pip install -r requirements.txt
cp .env.example .env
```

Set your API key in `.env`:

```ini
COINGECKO_API_KEY=CG-your_api_key_here
USE_PRO_API=false
```

## Scripts

```bash
python scripts/01_discover_categories.py
python scripts/02_list_markets.py --category tokenized-gold
python scripts/03_simple_price.py --ids pax-gold,tether-gold
python scripts/04_coin_detail.py --coin-id pax-gold
python scripts/05_market_chart.py --coin-id pax-gold --days 30
python scripts/06_ohlc_chart.py --coin-id pax-gold --days 30
python scripts/07_weekend_gap_view.py --coin-id pax-gold --days 30
```

Paid endpoint (Analyst+):

```bash
python scripts/08_ohlc_range_pro.py --coin-id pax-gold --from 2025-01-01 --to 2025-02-01 --interval daily
```

## Outputs

Generated files are saved under:

- `output/csv/`
- `output/charts/`
- `output/json/`

## Notes

- Demo plan is fully supported for scripts `01` to `07`.
- `08_ohlc_range_pro.py` is paid-plan only and will stop with a clear message in demo mode.

## Useful Links

- CoinGecko API Docs: https://docs.coingecko.com/
- CoinGecko API Pricing: https://www.coingecko.com/api/pricing
- Tokenized Gold category: https://www.coingecko.com/en/categories/tokenized-gold

## License

MIT
