import requests as rq
import json
import os

# Define a custom exception class
class KeyNotFoundError(Exception):
    pass

#PUB_URL = "https://api.coingecko.com/api/v3"
PRO_URL = "https://pro-api.coingecko.com/api/v3"

# Get API key from file (when running locally) or from env. variable (during CI)
def get_key():
    file = "/home/vikas/Documents/CG_pro_key.json"
    if os.path.exists(file):
        f = open(file)
        key_dict = json.load(f)
        return key_dict["key"]
    else:
        key = os.getenv('CG_PRO_KEY')
        if key is not None:
            return key
        else:
            raise KeyNotFoundError("API key is not available!")

# Switch between demo and pro accounts
#use_demo = {"accept": "application/json"}

use_pro = {
         "accept": "application/json",
         "x-cg-pro-api-key" : get_key()
}

def get_response(endpoint, headers, params, URL):
    url = "".join((URL, endpoint))
    response = rq.get(url, headers = headers, params = params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Failed to fetch data, check status code {response.status_code}")