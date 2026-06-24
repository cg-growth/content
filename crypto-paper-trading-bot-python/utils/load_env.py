import os
from dotenv import load_dotenv

load_dotenv()
cg_api_key = os.getenv("CG_API_KEY")
db_url = os.getenv("DATABASE_URL")

tp = float(os.getenv("TAKE_PROFIT"))
sl = float(os.getenv("STOP_LOSS"))
qty = float(os.getenv("ORDER_AMOUNT"))
price_change = float(os.getenv("PRICE_CHANGE"))
