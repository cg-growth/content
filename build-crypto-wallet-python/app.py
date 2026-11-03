import json
import os
from decimal import Decimal, InvalidOperation

import requests
from dotenv import load_dotenv
from eth_account import Account
from flask import Flask, jsonify, render_template, request, session
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput, ContractLogicError, Web3RPCError

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]

# Sepolia testnet by default, so you can test with free test ETH.
# Set ETH_RPC_URL to use another network or RPC provider.
rpc_url = os.environ.get("ETH_RPC_URL") or f"https://sepolia.infura.io/v3/{os.environ['INFURA_API_KEY']}"
web3 = Web3(Web3.HTTPProvider(rpc_url))

COINGECKO_API_KEY = os.environ["COINGECKO_DEMO_API_KEY"]
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

with open("erc20_abi.json") as f:
    erc20_abi = json.load(f)

# Private keys stay in server memory, never in the session cookie.
# Flask's default session is signed but not encrypted, so the browser can read it.
private_keys = {}


@app.route("/new_account", methods=["GET"])
def new_account():
    account = Account.create()
    private_key = Web3.to_hex(account.key)
    private_keys[account.address] = private_key
    session["address"] = account.address
    # The private key is returned once so you can back it up. Never share it.
    return jsonify({"address": account.address, "privateKey": private_key})


@app.route("/balance", methods=["GET"])
@app.route("/balance/<contract_address>", methods=["GET"])
def get_balance(contract_address=None):
    address = session.get("address")
    if not address:
        return jsonify({"error": "Create an account first."}), 400

    # No contract address: return the account's ETH balance
    if not contract_address:
        balance_wei = web3.eth.get_balance(address)
        return jsonify({"symbol": "ETH", "balance": str(Web3.from_wei(balance_wei, "ether"))})

    if not Web3.is_address(contract_address):
        return jsonify({"error": "Invalid contract address."}), 400

    contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=erc20_abi)
    try:
        raw_balance = contract.functions.balanceOf(address).call()
        decimals = contract.functions.decimals().call()
        symbol = contract.functions.symbol().call()
    except (BadFunctionCallOutput, ContractLogicError):
        return jsonify({"error": "No ERC-20 token found at this address on the connected network."}), 400

    balance = Decimal(raw_balance) / (Decimal(10) ** decimals)
    return jsonify({"symbol": symbol, "balance": str(balance), "raw_balance": str(raw_balance)})


@app.route("/send_transaction", methods=["POST"])
def send_transaction():
    address = session.get("address")
    if address not in private_keys:
        return jsonify({"error": "Create an account first."}), 400

    data = request.get_json()
    to_address = data.get("to", "")
    if not Web3.is_address(to_address):
        return jsonify({"error": "Invalid recipient address."}), 400
    try:
        value = Web3.to_wei(Decimal(str(data.get("amount"))), "ether")
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Invalid amount."}), 400

    try:
        txn = {
            "from": address,
            "to": Web3.to_checksum_address(to_address),
            "value": value,
            "nonce": web3.eth.get_transaction_count(address, "pending"),
            "chainId": web3.eth.chain_id,
        }
        # EIP-1559 fees: a tip for the validator plus room for the base fee to rise
        priority_fee = web3.eth.max_priority_fee
        base_fee = web3.eth.get_block("latest")["baseFeePerGas"]
        txn["maxPriorityFeePerGas"] = priority_fee
        txn["maxFeePerGas"] = 2 * base_fee + priority_fee
        txn["gas"] = web3.eth.estimate_gas(txn)

        signed_txn = Account.sign_transaction(txn, private_keys[address])
        txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    except (Web3RPCError, ValueError) as e:
        # For example, insufficient funds for gas and value
        return jsonify({"error": str(e)}), 400

    return jsonify({"transaction_hash": Web3.to_hex(txn_hash)})


@app.route("/market_chart/<contract_address>/<days>", methods=["GET"])
def get_market_chart(contract_address, days):
    response = requests.get(
        f"{COINGECKO_BASE_URL}/coins/ethereum/contract/{contract_address}/market_chart",
        params={"vs_currency": "usd", "days": days},
        headers={"x-cg-demo-api-key": COINGECKO_API_KEY},
        timeout=10,
    )
    # Or use the official CoinGecko Python SDK (pip install coingecko-sdk):
    # from coingecko_sdk import Coingecko
    # client = Coingecko(demo_api_key=COINGECKO_API_KEY, environment="demo")
    # market_chart = client.coins.contract.market_chart.get(
    #     contract_address, id="ethereum", vs_currency="usd", days=days
    # ).to_dict()
    if response.status_code != 200:
        return jsonify({"error": response.json()}), response.status_code
    return jsonify(response.json())


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
