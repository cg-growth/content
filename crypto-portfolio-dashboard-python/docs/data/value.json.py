import json
import sys
from portfolio import duration, target_currency, port_amount, port_curr
from data import get_hist_market
from helpers import get_prices_dict, create_breakdown_dict

breakdown_dict = None

for (curr, amount) in zip(port_curr, port_amount):
    curr_hist = get_hist_market(curr, target_currency, duration)
    curr_dict = get_prices_dict(curr_hist["prices"])

    # Correct for duplicate entry for latest date
    if len(curr_dict) > int(duration):
        curr_dict = curr_dict[0:int(duration)]

    if breakdown_dict is None:
        breakdown_dict = create_breakdown_dict(curr_dict, port_curr)

    for i in range(len(curr_dict)):
        daily_value = curr_dict[i]["price"] * amount
        breakdown_dict[i]["value"] += daily_value
        breakdown_dict[i][f"{curr}"] = daily_value

json.dump(breakdown_dict, sys.stdout)