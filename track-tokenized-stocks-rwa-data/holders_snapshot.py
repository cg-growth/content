import requests
from config import HEADERS, ONCHAIN_URL

def get_holder_snapshot(network_id, token_address):
    url = f"{ONCHAIN_URL}/networks/{network_id}/tokens/{token_address}/info"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["data"]["attributes"]["holders"]

# SDK equivalent: client.onchain.networks.tokens.info.get(token_address, network=network_id)

if __name__ == "__main__":
    holders = get_holder_snapshot("solana", "Xsc9qvGR1efVDFGLrVsmkzv3qi45LTBjeUKSPmx9qEh")  # Nvidia xStock; any tokenized stock works
    print("Total holders:", holders["count"])
    print("Distribution:", holders["distribution_percentage"])
