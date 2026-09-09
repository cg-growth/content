import requests
from config import BASE_URL, HEADERS

def get_rwa_by_id(rwa_id):
    url = f"{BASE_URL}/rwas/{rwa_id}"
    # tokens and tokenized_market_data default to false.
    # Leave either one out and you will only get bare metadata back.
    params = {"tokens": "true", "tokenized_market_data": "true"}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

def get_issuer(issuer_id):
    url = f"{BASE_URL}/rwas/issuers/{issuer_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    rwa = get_rwa_by_id("openai-pre-ipo")
    print(f"{rwa['name']} is tracked as {len(rwa['tokens'])} separate tokens:")
    for token in rwa["tokens"]:
        # Not every token lists a platform yet, so only add the clause when one exists
        platform = next(iter(token["platforms"]), None)
        platform_note = f" on {platform}" if platform else ""
        print(f" - {token['name']} ({token['symbol'].upper()}){platform_note}, issued by {token['issuer_details']['name']}")

    issuer = get_issuer("republic-tokenized-pre-ipo-assets")
    print(f"\n{issuer['name']} has tokenized {len(issuer['tokens'])} assets worth ${issuer['market_cap']:,.0f} total")
    for t in issuer["tokens"]:
        print(" -", t["name"])
