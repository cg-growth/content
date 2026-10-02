import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COINGECKO_PRO_API_KEY")
BASE_URL = "https://pro-api.coingecko.com/api/v3"
HEADERS = {"x-cg-pro-api-key": API_KEY}

def get_balances(address, networks):
    """Fetch a wallet's token balances across networks."""
    url = f"{BASE_URL}/onchain/wallets/{address}/balances"
    response = requests.get(url, headers=HEADERS, params={"networks": networks}, timeout=20)
    response.raise_for_status()
    return response.json()

def get_trades(network, address, **params):
    """Fetch a wallet's trades on a single network."""
    url = f"{BASE_URL}/onchain/networks/{network}/wallets/{address}/trades"
    response = requests.get(url, headers=HEADERS, params=params, timeout=20)
    response.raise_for_status()
    return response.json()

def get_transfers(network, address, **params):
    """Fetch a wallet's token transfers on a single network."""
    # SDK equivalent (pip install coingecko_sdk):
    # from coingecko_sdk import Coingecko
    # client = Coingecko()  # reads COINGECKO_PRO_API_KEY automatically
    # response = client.onchain.networks.wallets.transfers.get(address, network=network, **params)
    url = f"{BASE_URL}/onchain/networks/{network}/wallets/{address}/transfers"
    response = requests.get(url, headers=HEADERS, params=params, timeout=20)
    response.raise_for_status()
    return response.json()

def get_pnl(address, networks):
    """Fetch a wallet's realized and unrealized PnL across networks in one VM family."""
    url = f"{BASE_URL}/onchain/wallets/{address}/pnl"
    response = requests.get(url, headers=HEADERS, params={"networks": networks}, timeout=20)
    response.raise_for_status()
    return response.json()
