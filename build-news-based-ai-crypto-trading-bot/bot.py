import time
import requests
from config import BASE_URL, HEADERS, MIN_MARKET_CAP_USD, MIN_VOLUME_USD
from fetch_news import fetch_latest_news
from score_news import score_headline
from confirm_signal import should_trade, should_exit
from paper_trader import PaperPortfolio

seen_urls = set()
portfolio = PaperPortfolio()

def get_portfolio_pnl(conn):
    """Realized PnL from closed trades plus unrealized PnL from open
    positions, both powered by a single bulk price call."""
    positions = conn.execute(
        "SELECT coin_id, qty, entry_price FROM positions").fetchall()
    trades = conn.execute(
        "SELECT coin_id, side, qty, price FROM trades").fetchall()

    coin_ids = {row[0] for row in positions} | {row[0] for row in trades}
    if not coin_ids:
        return {"realized_usd": 0.0, "unrealized_usd": 0.0, "positions": []}

    # A single call covers every coin the bot has ever touched;
    # /simple/price accepts up to 515 IDs per request.
    response = requests.get(f"{BASE_URL}/simple/price", headers=HEADERS,
        params={"ids": ",".join(coin_ids), "vs_currencies": "usd"})
    response.raise_for_status()
    prices = {coin_id: data["usd"] for coin_id, data in response.json().items()}

    realized = 0.0
    cost_basis = {}
    for coin_id, side, qty, price in trades:
        if side == "BUY":
            cost_basis.setdefault(coin_id, []).append([qty, price])
        elif side == "SELL":
            remaining = qty
            while remaining > 0 and cost_basis.get(coin_id):
                lot_qty, lot_price = cost_basis[coin_id][0]
                matched = min(remaining, lot_qty)
                realized += matched * (price - lot_price)
                lot_qty -= matched
                remaining -= matched
                if lot_qty <= 0:
                    cost_basis[coin_id].pop(0)
                else:
                    cost_basis[coin_id][0][0] = lot_qty

    unrealized = 0.0
    open_positions = []
    for coin_id, qty, entry_price in positions:
        current_price = prices.get(coin_id)
        if current_price is None:
            continue
        pnl = qty * (current_price - entry_price)
        unrealized += pnl
        open_positions.append({"coin_id": coin_id, "qty": qty, "pnl_usd": pnl})

    return {"realized_usd": realized, "unrealized_usd": unrealized,
            "positions": open_positions}

def run_cycle():
    for article in fetch_latest_news(per_page=20):
        # The same story is syndicated across outlets and reappears on every
        # poll. Without this check the bot buys the same news repeatedly
        if article["url"] in seen_urls:
            continue
        seen_urls.add(article["url"])

        coin_ids = article["related_coin_ids"]
        if not coin_ids:
            portfolio.log_signal(None, article["title"], None, None,
                                 executed=False, reason="no related coin")
            continue

        response = requests.get(f"{BASE_URL}/coins/markets", headers=HEADERS, params={
            "vs_currency": "usd", "ids": ",".join(coin_ids),
            "price_change_percentage": "1h,24h",
        })
        response.raise_for_status()
        candidates = sorted(
            (c for c in response.json()
             if (c["market_cap"] or 0) >= MIN_MARKET_CAP_USD
             and (c["total_volume"] or 0) >= MIN_VOLUME_USD),
            key=lambda c: c["market_cap"], reverse=True)

        if not candidates:
            # Logged with no coin_id, since nothing matched survived the
            # size and liquidity filter at all
            portfolio.log_signal(None, article["title"], None, None,
                                 executed=False, reason="no tradeable coin")
            continue

        signal = score_headline(article["title"], article["source_name"])
        coin = candidates[0]

        if portfolio.has_position(coin["id"]) and should_exit(
                signal["score"], signal["confidence"], coin):
            qty = portfolio.sell(coin["id"], coin["current_price"],
                                article["title"], signal["score"])
            print(f"       SELL {qty:.6f} {coin['symbol'].upper()} @ ${coin['current_price']:,.2f}")
            continue

        ok, reason = should_trade(signal["score"], signal["confidence"], coin)

        if ok and portfolio.in_cooldown(coin["id"]):
            ok, reason = False, "cooldown active"

        portfolio.log_signal(coin["id"], article["title"], signal["score"],
                             signal["confidence"], executed=ok, reason=reason)

        print(f"{signal['score']:+.2f} {coin['id']:<10} {article['title'][:46]}")
        if not ok:
            print(f"       skip: {reason}")
            continue

        qty = portfolio.buy(coin["id"], coin["current_price"],
                            article["title"], signal["score"])
        print(f"       BUY {qty:.6f} {coin['symbol'].upper()} @ ${coin['current_price']:,.2f}")

if __name__ == "__main__":
    while True:
        run_cycle()
        pnl = get_portfolio_pnl(portfolio.conn)
        print(f"Realized ${pnl['realized_usd']:+,.2f} | "
              f"Unrealized ${pnl['unrealized_usd']:+,.2f}")
        time.sleep(600)
