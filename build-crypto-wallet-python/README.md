> Read the full article: [Developers' Guide: How to Build a Crypto Wallet Using Python](https://www.coingecko.com/learn/build-crypto-wallet-python)

# Ethereum Wallet Application

This application is a simple Ethereum wallet that allows you to create a new Ethereum account, check the balance of an ERC20 token for a given Ethereum address, and fetch the market chart data for a given ERC20 contract.

## Prerequisites

- Python 3.6 or higher
- Flask
- Web3
- requests

You can install the necessary Python packages using pip:

```bash
pip install flask web3 requests
```
## Running the Application

1. Clone the repository and navigate to the project directory.
2. Replace `'YOUR_INFURA_PROJECT_ID'`, `'your-secret-key'`, and `'YOUR_PASSWORD'` in the Python script with your actual Infura project ID, secret key, and password.
3. Run the application:

```bash
python app.py
```
4. Open a web browser and navigate to `http://localhost:5000`.

## Endpoints

- `GET /new_account`: Creates a new Ethereum account and returns the private key and address.
- `GET /balance/<contract_address>`: Returns the balance of the ERC20 token for the Ethereum address stored in the session.
- `POST /send_transaction`: Send Ether to other Ethereum addresses
- `GET /market_chart/<contract_address>/<days>`: Returns the market chart data for the given ERC20 contract in USD for the specified number of days.

## Files

- `app.py`: The main Python script that runs the application.
- `erc20_abi.json`: The ABI for the ERC20 token standard.
- `templates/index.html`: The HTML template for the application's user interface.
## Output
![image](https://github.com/rollendxavier/crypto_wallet_coingecko/assets/42246854/354d85de-58db-4586-b639-48def0871c70)

For more details, please refer to the article published in the [coingecko](https://www.coingecko.com/learn/build-crypto-wallet-python).
