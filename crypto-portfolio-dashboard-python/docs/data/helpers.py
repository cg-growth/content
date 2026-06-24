import datetime

def get_prices_dict(prices):

    prices_dict = []

    for i in range(len(prices)):
        # Convert to seconds
        s = prices[i][0] / 1000
        prices_dict.append({'time' : datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d'),
                            'price' : prices[i][1]})
        
    return prices_dict

def initialize_dict(port_curr):

    # Initialize dict with keys for all currencies
    port_value = [0.0 for i in range(len(port_curr))]
    breakdown = {port_curr[i] : port_value[i] for i in range(len(port_curr))}

    # Add key to store total value
    breakdown['value'] = 0.0

    return breakdown

def create_breakdown_dict(curr_dict, port_curr):

    # Create a list of dicts
    breakdown_dict = []
    for i in range(len(curr_dict)):
        breakdown = initialize_dict(port_curr)
        breakdown['time'] = curr_dict[i]["time"]
        breakdown_dict.append(breakdown)

    return breakdown_dict