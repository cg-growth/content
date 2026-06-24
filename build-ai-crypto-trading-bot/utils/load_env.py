import os
from dotenv import load_dotenv

load_dotenv()
cg_api_key = os.getenv("CG_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

prompt_template = open(os.getenv("PROMPT_TEMPLATE"), "r").read()

# Trade Settingd
tp = float(os.getenv("TAKE_PROFIT"))
sl = float(os.getenv("STOP_LOSS"))
qty = float(os.getenv("ORDER_AMOUNT"))
price_change = float(os.getenv("PRICE_CHANGE"))


# Pool Safety Checks
min_volume_24h = float(os.getenv("MIN_VOLUME_24H"))
min_reserves_usd = float(os.getenv("MIN_RESERVES_USD"))
min_buys_24h = float(os.getenv("MIN_BUYS_24H"))
