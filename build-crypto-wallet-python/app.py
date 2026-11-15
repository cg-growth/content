"""Multi-chain crypto wallet: Flask back end.

The browser creates the private key and signs transactions (static/wallet.js).
This server never sees the key. It only:
  - calls CoinGecko API (so your API key stays off the browser), and
  - forwards already-signed transactions to Ethereum Sepolia.
"""
import os

import coingecko_sdk
from coingecko_sdk import Coingecko
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from web3 import Web3
from web3.exceptions import Web3RPCError

load_dotenv()
app = Flask(__name__)
app.json.sort_keys = False  # keep the network order below

# --- CoinGecko API -------------------------------------------------------
# Wallet endpoints need an Analyst plan key or above ("pro").
# With a free Demo key, the wallet basics and price chart still work.
CG_PLAN = os.environ.get("COINGECKO_PLAN", "pro").lower()
CG_KEY = os.environ["COINGECKO_API_KEY"]
if CG_PLAN == "pro":
    client = Coingecko(pro_api_key=CG_KEY, environment="pro")
else:
    client = Coingecko(demo_api_key=CG_KEY, environment="demo")

# EVM networks this wallet queries together in one call.
# Every network in one balances or PnL request must share a VM family.
WALLET_NETWORKS = {
    "eth": "Ethereum", "base": "Base", "bsc": "BNB Chain", "polygon_pos": "Polygon",
    "arbitrum": "Arbitrum", "optimism": "Optimism", "avax": "Avalanche",
    "robinhood": "Robinhood", "stable": "Stable", "linea": "Linea", "arc": "Arc",
    "monad": "Monad", "unichain": "Unichain", "zksync": "zkSync", "world-chain": "World Chain",
}
NETWORKS_PARAM = ",".join(WALLET_NETWORKS)

# A public mainnet address with real activity, used when you don't enter one.
SAMPLE_ADDRESS = "0x7942262a7a5637e6eb0eec9b91b55ec232141f87"

# --- Ethereum Sepolia (send and receive) --------------------------------
rpc_url = os.environ.get("ETH_RPC_URL") or f"https://sepolia.infura.io/v3/{os.environ.get('INFURA_API_KEY', '')}"
web3 = Web3(Web3.HTTPProvider(rpc_url))


def needs_paid_plan():
    """Wallet endpoints are on the Analyst plan and above."""
    if CG_PLAN != "pro":
        return jsonify({"upgrade": True, "error": "Wallet data needs an Analyst plan API key or above."}), 402
    return None


def api_error(e):
    status = getattr(e, "status_code", 502)
    return jsonify({"error": str(getattr(e, "message", e))}), status


# --- Pages ---------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/config")
def config():
    return jsonify({"plan": CG_PLAN, "sample_address": SAMPLE_ADDRESS, "networks": WALLET_NETWORKS})


# --- Portfolio: every token a wallet holds, across networks, in one call -
@app.route("/api/portfolio/<address>")
def portfolio(address):
    if (blocked := needs_paid_plan()):
        return blocked
    if not Web3.is_address(address):
        return jsonify({"error": "Invalid address."}), 400
    try:
        # REST equivalent, if you prefer raw HTTP requests:
        # GET https://pro-api.coingecko.com/api/v3/onchain/wallets/{address}/balances?networks=eth,base,...
        # with your key in the x-cg-pro-api-key header
        data = client.onchain.wallets.balances.get(
            address,
            networks=request.args.get("networks", NETWORKS_PARAM),
            value_usd_min=1,           # skip dust
            reserve_in_usd_min=10000,  # skip illiquid and spam tokens
            per_page=50,
        ).to_dict()
    except coingecko_sdk.APIError as e:
        return api_error(e)

    attrs = data["data"]["attributes"]
    # Add logos from CoinGecko coin data, joined on coingecko_coin_id
    coin_ids = sorted({b["coingecko_coin_id"] for b in attrs["balances"] if b.get("coingecko_coin_id")})
    logos = {}
    if coin_ids:
        try:
            markets = client.coins.markets.get(vs_currency="usd", ids=",".join(coin_ids), per_page=250)
            logos = {m.id: m.image for m in markets}
        except coingecko_sdk.APIError:
            pass  # logos are optional
    for b in attrs["balances"]:
        b["logo"] = logos.get(b.get("coingecko_coin_id"))

    # Tokens without a coin ID: use their onchain token image, up to 30 addresses per network
    no_logo = {}
    for b in attrs["balances"]:
        if not b["logo"]:
            no_logo.setdefault(b["network"], []).append(b["address"])
    for network, addresses in no_logo.items():
        try:
            tokens = client.onchain.networks.tokens.multi.get_addresses(",".join(addresses[:30]), network=network)
        except coingecko_sdk.APIError:
            continue
        images = {t.attributes.address.lower(): t.attributes.image_url for t in tokens.data}
        for b in attrs["balances"]:
            if not b["logo"] and b["network"] == network:
                b["logo"] = images.get(b["address"].lower())
    return jsonify(attrs)


# --- Activity: trades (buy/sell) and transfers (in/out) on one network ---
@app.route("/api/activity/<address>")
def activity(address):
    if (blocked := needs_paid_plan()):
        return blocked
    network = request.args.get("network", "eth")
    try:
        trades = client.onchain.networks.wallets.trades.get(address, network=network).to_dict(mode="json")
        transfers = client.onchain.networks.wallets.transfers.get(address, network=network).to_dict(mode="json")
    except coingecko_sdk.APIError as e:
        return api_error(e)

    feed = [
        {"type": t["attributes"]["kind"], "time": t["attributes"]["block_timestamp"],
         "tx_hash": t["attributes"]["tx_hash"], "usd": t["attributes"]["volume_in_usd"],
         "dex": t["attributes"]["pool_dex"]}
        for t in trades["data"]
    ] + [
        {"type": t["attributes"]["direction"], "time": t["attributes"]["block_timestamp"],
         "tx_hash": t["attributes"]["tx_hash"], "symbol": t["attributes"]["symbol"],
         "amount": t["attributes"]["amount"]}
        for t in transfers["data"]
    ]
    feed.sort(key=lambda item: item["time"], reverse=True)
    return jsonify({"network": network, "items": feed})


# --- PnL: realized and unrealized, per network and per token ------------
@app.route("/api/pnl/<address>")
def pnl(address):
    if (blocked := needs_paid_plan()):
        return blocked
    try:
        data = client.onchain.wallets.pnl.get(
            address,
            networks=request.args.get("networks", NETWORKS_PARAM),
            sort="realized_pnl_usd_desc",
        ).to_dict()
    except coingecko_sdk.APIError as e:
        return api_error(e)
    return jsonify(data["data"]["attributes"])


# --- Price chart for a token (works on the Demo plan) --------------------
@app.route("/api/chart/<coin_id>")
def chart(coin_id):
    try:
        data = client.coins.market_chart.get(coin_id, vs_currency="usd", days=request.args.get("days", "30"))
    except coingecko_sdk.APIError as e:
        return api_error(e)
    return jsonify({"prices": data.prices})


# --- Sepolia: balance, transaction parameters and broadcast --------------
@app.route("/api/sepolia/<address>")
def sepolia_account(address):
    if not Web3.is_address(address):
        return jsonify({"error": "Invalid address."}), 400
    address = Web3.to_checksum_address(address)
    try:
        latest = web3.eth.get_block("latest")
        priority_fee = web3.eth.max_priority_fee
        return jsonify({
            "balance_eth": str(Web3.from_wei(web3.eth.get_balance(address), "ether")),
            "nonce": web3.eth.get_transaction_count(address, "pending"),
            "chain_id": web3.eth.chain_id,
            "max_priority_fee_per_gas": priority_fee,
            "max_fee_per_gas": 2 * latest["baseFeePerGas"] + priority_fee,
        })
    except Exception as e:  # RPC unreachable or misconfigured
        return jsonify({"error": f"Sepolia RPC error: {e}"}), 502


@app.route("/api/sepolia/send", methods=["POST"])
def sepolia_send():
    raw_tx = (request.get_json(silent=True) or {}).get("raw_tx", "")
    if not raw_tx.startswith("0x"):
        return jsonify({"error": "Send a signed transaction (0x-prefixed hex)."}), 400
    try:
        tx_hash = web3.eth.send_raw_transaction(raw_tx)
    except (Web3RPCError, ValueError) as e:
        return jsonify({"error": str(e)}), 400  # for example, insufficient funds
    return jsonify({"tx_hash": Web3.to_hex(tx_hash)})


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
