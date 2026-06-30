from cg_client import get

payload = get("/onchain/networks")
for network in payload["data"][:5]:
    print(network["id"], network["attributes"]["name"])
