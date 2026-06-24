from api import get_response, PRO_URL, use_pro

def get_hist_market(coin_id, currency, duration):

    params = {
               "vs_currency": currency,
               "days": duration,
               "precision": 2
             }
    
    hist_data = get_response(f"/coins/{coin_id}/market_chart", use_pro, params, PRO_URL)

    return hist_data
