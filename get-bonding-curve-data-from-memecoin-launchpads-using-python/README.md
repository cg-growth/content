> Read the full article: [How to Get Bonding Curve Data from Memecoin Launchpads Using Python](https://www.coingecko.com/learn/get-bonding-curve-data-from-memecoin-launchpads-using-python)

> Read the full article: [How to Get Bonding Curve Data from Memecoin Launchpads Using Python](https://www.coingecko.com/learn/get-bonding-curve-data-from-memecoin-launchpads-using-python)

# Crypto Bonding Curve and Graduation Alert Bot

This repository contains a Python-based Crypto Alert Bot that monitors cryptocurrency token graduations,
tracks new pools, and sends email alerts. It leverages APIs to fetch token data, stores historical
information using DuckDB, and automates alerting via Gmail.

## Features

1. Token Graduation Monitoring
    - Tracks tokens across different networks (e.g., Solana)
    - Identifies tokens nearing or reaching 100% graduation
    - Sends email alerts when tokens complete their graduation process

2. New Pool Detection
    - Fetches newly created pools from an API
    - Analyzes top pools by market cap or other metrics
    - Groups tokens by network for further tracking

3. Database Integration (DuckDB)
    - Stores token addresses and networks in a local DuckDB database
    - Enables persistent tracking of tokens across sessions
    - Supports periodic updates of token status with timestamps

4. Email Notifications
    - Sends HTML-formatted email alerts via Gmail SMTP
    - Configurable thresholds for triggering alerts
    - Customizable email content and recipients

## Code structure

### Core modules

| Module | Description |
|--------|-------------|
| get_new_pools() | Fetches new pools from API and sorts them by specified criteria |
| track_status() | Tracks token status including graduation percentage |
| send_email() | Sends email alerts based on token graduation |
| track_status_all() | Aggregates token statuses from multiple networks |
| track_status_all_from_db() | Reads tokens from DuckDB and tracks their status |
| DuckDB Integration | Stores and retrieves token addresses and networks for persistent tracking |

## Key functions

- `get_app_password()` – Retrieves Gmail app password from a JSON file
- `send_graduation_alert()` – Sends HTML email via SMTP
- `get_network_token_add_dict()` – Groups token addresses by network
- `track_status_all_from_db()` – Updates token status from database

## Streamlit app

### Key components

#### Database Integration
- Uses DuckDB to read token status data from Token_data.duckdb
- Implements caching for efficient data loading with @st.cache_data decorator
- Reads all data from the token_status table

#### Streamlit UI
- Creates a web interface with title "Token Data Viewer"
- Displays raw data in a scrollable table format
- Provides interactive token selection via multiselect dropdown
- Shows graduation percentage over time using Altair charts

#### Data Visualization
- Plots grad_pert (graduation percentage) against time for selected tokens
- Supports multiple token selection with interactive chart
- Includes tooltips for detailed information
- Automatically handles datetime conversion for timestamps

#### Features
- Interactive Dashboard: Users can select specific tokens to visualize
- Time Series Analysis: Shows how token graduation progresses over time
- Responsive Design: Uses Streamlit's container width for optimal display
- Error Handling: Filters out null values before plotting

## Setup instructions

Prerequisites:
- Python 3.8+
- Required packages: pandas, duckdb, smtplib, email, json, time

Install dependencies:
```
pip install pandas duckdb
```

Configuration:
1. Create a Gmail_app_pass.json file in Documents with the following structure:
```
{
  "pass": "your_gmail_app_password"
}
```
2. Ensure access to the API endpoints used in `get_response()` function
3. Set up DuckDB database (Token_data.duckdb) to store token data

## Usage examples

1. Track tokens from new pools
```
df_all_status = track_status_all("market_cap_usd", 200)
```

2. Send graduation alerts
```
send_email(list_of_tokens, "solana", 95)
```

3. Update token status periodically
```
while True:
    time.sleep(300)
    df_status_to_write = track_status_all_from_db(tokens_dict)
    con.execute("INSERT INTO token_status SELECT * FROM df_status_to_write")
```

4. Run the script with `streamlit run app.py` to launch the web application. The interface allows users to
explore token data and visualize graduation trends over time.

## Notes
- The bot uses DuckDB for lightweight, fast local storage.
- Email alerts are sent only for tokens that have completed graduation (completed == True)
- The bot can be scheduled to run periodically using cron jobs or task schedulers

## Future enhancements
- Add support for more networks (Ethereum, BSC, etc.)
- Implement Slack or Discord notifications
- Add filtering options for specific token types or categories
- Store full token metadata in the database for richer analysis

## License
This project is licensed under the MIT License. See the LICENSE file for details.