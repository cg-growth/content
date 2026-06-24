> Read the full article: [How to Build a Pump.fun Sniper Bot in Python](https://www.coingecko.com/learn/how-to-build-pump-fun-sniper-bot-in-python)

# Token Sniper Bot (CoinGecko Onchain)

This repo contains two Jupyter notebooks that fetch new pools from CoinGecko, stream onchain token prices over
WebSocket, persist price ticks, and simulate simple trade signals.

## Notebooks

- `CG_sniper_bot.ipynb`
  - Fetches new pools, filters recent pools, and builds a token list.
  - Streams Onchain Simple Token Price data from CoinGecko WebSocket
  - Writes price ticks to DuckDB or PostgreSQL

- `CG_run_simulation.ipynb`
  - Loads `token_list` and reads price data
  - Simulates trade signals (take profit / stop loss / monitoring)
  - Prints colorized, readable logs.

## Requirements

- Python 3.10+
- Packages used in the notebooks:
  - `pandas`, `requests`, `websockets`, `duckdb`, `psycopg`, `python-dotenv`, `numpy`, `plotly`

## Environment variables

Create a `.env` file (do not commit it):

```
CG_DEMO_API_KEY=...
CG_PRO_API_KEY=...
CG_ANALYST_API_KEY=...
```

## Quick start

1. Install dependencies (example):
   
   ```bash
   python3 -m pip install pandas requests websockets duckdb psycopg[binary] python-dotenv numpy plotly
   ```

2. Open and run `CG_sniper_bot.ipynb`:
   - Fetch and analyze new pools
   - Build `token_list`
   - Stream WS data and write ticks to DuckDB or PostgreSQL

3. Open and run `CG_run_simulation.ipynb`:
   - Load `token_list`
   - Read latest ticks and simulate trades

## Data storage options

- **DuckDB**: Simple local storage for single-notebook workflows
- **PostgreSQL**: Supports multi-notebook concurrent access and persistence

## Trade simulation logic

- Entry price = first observed price for a token
- Take profit if `price > entry * 1.1` (or 1.2 in some examples)
- Stop loss if `price < entry * 0.9` (or 0.8 in some examples)
- Otherwise status is `monitoring`

## Architecture diagram

```mermaid
flowchart LR
    A["CoinGecko API (New Solana Pools)"] --> B["Scan Module: Pool Discovery"]
    B --> C["Filter Module: Liquidity & FDV Checks"]
    C --> D["Execution Engine: Paper / Live Trades"]
    D --> E["WebSocket Monitor: Price Tracking"]
    E --> F["Exit Logic: Take Profit / Stop Loss"]
```

## Notes

- The WebSocket endpoint expects a subscription to `OnchainSimpleTokenPrice` and a `set_tokens` message with `network_id:token_addresses`
- For PostgreSQL, set your session timezone (e.g., `Europe/Berlin`) to display timestamps in CET/CEST
- Do not commit API keys or credentials to the repo

## PostgreSQL quick setup (Linux, macOS, Windows)

Linux (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl status postgresql
sudo -u postgres psql
```

In `psql`:

```sql
CREATE USER myuser WITH PASSWORD 'mypassword';
CREATE DATABASE mydb OWNER myuser;
\q
```

macOS (Homebrew):

```bash
brew install postgresql@16
brew services start postgresql@16
psql -d postgres
```

In `psql`:

```sql
CREATE USER myuser WITH PASSWORD 'mypassword';
CREATE DATABASE mydb OWNER myuser;
\q
```

Windows:

1. Download and install PostgreSQL from https://www.postgresql.org/download/windows/
2. Use the Stack Builder/installer to set a password for the `postgres` user.
3. Open SQL Shell (psql) and run:

```sql
CREATE USER myuser WITH PASSWORD 'mypassword';
CREATE DATABASE mydb OWNER myuser;
\q
```

Connection string example:

```
postgresql://myuser:mypassword@localhost:5432/mydb
```
