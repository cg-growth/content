import os
from dotenv import load_dotenv

load_dotenv()
cg_api_key = os.getenv("CG_API_KEY")
take_profit = 1.1  # 10%
stop_loss = 0.9  # -10%
size = 0.1  # 10% from total amount
total_amount = 10000000
