import json
import streamlit as st
import pandas as pd
import requests
import mplfinance as mpf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns  # Add this line to import seaborn

def parse_ohlcv_data(json_payload):
    # Extract OHLCV list and metadata from the payload
    ohlcv_list = json_payload["data"]["attributes"]["ohlcv_list"]
    metadata = json_payload["meta"]

    # Parse OHLCV data into a DataFrame
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(ohlcv_list, columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    # Return both the DataFrame and metadata
    return df, metadata


def parse_crypto_pools(json_payload):
    # Convert the JSON payload to a Python dictionary
    data = json_payload

    # List to hold parsed pool data
    parsed_pools = []

    # Iterate through each pool in the data
    for pool in data['data']:
        # Extract relevant information from each pool
        pool_info = {
            'address': pool['attributes']['address'],
            'name': pool['attributes']['name'],
            'pool_created_at': pool['attributes']['pool_created_at'],
            'fdv_usd': pool['attributes'].get('fdv_usd'),
            'market_cap_usd': pool['attributes'].get('market_cap_usd'),
            'volume_usd_h1': pool['attributes']['volume_usd']['h1'],
            'volume_usd_h24': pool['attributes']['volume_usd']['h24'],
            'price_change_percentage_h1': json.loads(pool['attributes']['price_change_percentage']['h1']),
            'price_change_percentage_h24': json.loads(pool['attributes']['price_change_percentage']['h24']),
            'transactions_h1_buys': pool['attributes']['transactions']['h1']['buys'],
            'transactions_h1_sells': pool['attributes']['transactions']['h1']['sells'],
        }
        parsed_pools.append(pool_info)

    return parsed_pools

def plot_ohlcv(df):
    # Ensure the DataFrame is sorted by timestamp in ascending order
    df_sorted = df.sort_values('timestamp').set_index('timestamp')
    mpf.plot(df_sorted, type='candle', style='charles',
             title='OHLCV Chart', ylabel='Price', ylabel_lower='Volume',
             volume=True, figratio=(16, 8), show_nontrading=False)
    
# Function to process the JSON data into a DataFrame
def process_data(data):
    def flatten(d, parent_key='', sep='_'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    # Flatten each pool's attributes and create a DataFrame
    flat_data = [flatten(pool['attributes']) for pool in data['data']]
    return pd.DataFrame(flat_data)

# Function to get top 3 pairs with the greatest 1-hour volume change
def get_top_changes(df, column_name='price_change_percentage_h1'):
    # Ensure the column is of type float
    df[column_name] = df[column_name].astype(float)
    # Sort the DataFrame based on the volume change column
    top_changes = df.sort_values(by=column_name, ascending=False).head(3)
    # Include the 'transactions' column in the returned DataFrame
    return top_changes[['name', column_name, 'transactions_h1_sells', 'transactions_h1_buys']]

# Function to create a pie chart for transaction types
def plot_transaction_types(df):
    trans_types = pd.DataFrame(df['transactions'].tolist()).h1.apply(pd.Series)
    buys = trans_types['buys'].sum()
    sells = trans_types['sells'].sum()
    fig, ax = plt.subplots()
    ax.pie([buys, sells], labels=['Buys', 'Sells'], autopct='%1.1f%%')
    plt.tight_layout()
    return fig

def plot_price_change(df, log_scale=False):
    pool_names = df['name']
    # Directly use the float values from the series
    price_changes_24h = [float(change) if change else 0 for change in df['price_change_percentage_h1']]
    fig, ax = plt.subplots()
    sns.barplot(x='price_change_percentage_h1', y='name', data=df, ax=ax)
    ax.set(xlabel='Price Change Percentage (24h)', title='Price Change Percentage (24h) by Pool')
    if log_scale:
        ax.set_xscale('log')

    return fig