"""
High-Frequency Crypto Copy Trading Bot
======================================
A sophisticated copy trading bot that uses CoinGecko API to:
1. Scout profitable tokens and pools using Megafilter/Trending endpoints
2. Analyze wallet profitability using on-chain trade data
3. Execute copy trades using WebSocket for real-time trade detection

Disclaimer: This is for educational purposes only and not financial advice.
"""

import os
import json
import time
import asyncio
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Configuration
# =============================================================================
CG_API_KEY = os.getenv("CG_PRO_API_KEY") or os.getenv("CG_DEMO_API_KEY")
CG_BASE_URL = "https://pro-api.coingecko.com/api/v3/onchain"  # Pro API for paid features
CG_DEMO_URL = "https://api.coingecko.com/api/v3/onchain"      # Demo API for free endpoints

# Use Pro API if Pro key available, otherwise Demo
if os.getenv("CG_PRO_API_KEY"):
    BASE_URL = CG_BASE_URL
    API_KEY = os.getenv("CG_PRO_API_KEY")
    print("✓ Using CoinGecko Pro API")
else:
    BASE_URL = CG_DEMO_URL
    API_KEY = os.getenv("CG_DEMO_API_KEY")
    print("✓ Using CoinGecko Demo API")

# Blockscout API for transaction verification
BLOCKSCOUT_BASE_URL = "https://eth.blockscout.com/api/v2"

# Headers for CoinGecko API
HEADERS = {
    "accept": "application/json",
    "x-cg-pro-api-key": API_KEY
}

# =============================================================================
# Helper Functions
# =============================================================================
def cg_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to CoinGecko API with error handling and rate limiting."""
    url = f"{BASE_URL}{endpoint}"
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
            
            if response.status_code == 429:
                print(f"⚠ Rate limited. Waiting {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
                continue
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt == 2:
                print(f"✗ API request failed: {e}")
                raise
            time.sleep(1)
    
    return {}


def format_number(num: float, decimals: int = 2) -> str:
    """Format large numbers with K, M, B suffixes."""
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.{decimals}f}B"
    elif num >= 1_000_000:
        return f"${num / 1_000_000:.{decimals}f}M"
    elif num >= 1_000:
        return f"${num / 1_000:.{decimals}f}K"
    return f"${num:.{decimals}f}"


# =============================================================================
# STEP 1: Find Profitable Tokens and Pools
# =============================================================================
def get_trending_pools(network: str = "eth", limit: int = 10) -> pd.DataFrame:
    """
    Fetch trending pools on a specific network using the free trending_pools endpoint.
    
    This endpoint is available on the Demo API and returns pools that are currently
    trending based on volume and activity.
    
    Args:
        network: Network ID (e.g., 'eth', 'base', 'arbitrum')
        limit: Maximum number of pools to return
    
    Returns:
        DataFrame with trending pool data
    """
    print(f"\n🔍 Fetching trending pools on {network}...")
    
    endpoint = f"/networks/{network}/trending_pools"
    params = {"include": "base_token,quote_token"}
    
    try:
        data = cg_request(endpoint, params)
        pools = data.get("data", [])[:limit]
        
        if not pools:
            print("No trending pools found.")
            return pd.DataFrame()
        
        # Parse pool data into structured format
        pool_data = []
        for pool in pools:
            attr = pool.get("attributes", {})
            relationships = pool.get("relationships", {})
            
            # Get base token info
            base_token = relationships.get("base_token", {}).get("data", {})
            quote_token = relationships.get("quote_token", {}).get("data", {})
            
            pool_data.append({
                "pool_address": attr.get("address", ""),
                "pool_name": attr.get("name", "Unknown"),
                "dex": relationships.get("dex", {}).get("data", {}).get("id", "unknown"),
                "base_token_symbol": attr.get("base_token_symbol", ""),
                "quote_token_symbol": attr.get("quote_token_symbol", ""),
                "price_usd": float(attr.get("base_token_price_usd", 0) or 0),
                "volume_24h": float(attr.get("volume_usd", {}).get("h24", 0) or 0),
                "liquidity_usd": float(attr.get("reserve_in_usd", 0) or 0),
                "price_change_24h": float(attr.get("price_change_percentage", {}).get("h24", 0) or 0),
                "transactions_24h": int(attr.get("transactions", {}).get("h24", {}).get("buys", 0) or 0) + 
                                   int(attr.get("transactions", {}).get("h24", {}).get("sells", 0) or 0)
            })
        
        df = pd.DataFrame(pool_data)
        
        print(f"✓ Found {len(df)} trending pools")
        print("\n📊 Top Trending Pools:")
        print("-" * 80)
        
        for i, row in df.head(5).iterrows():
            print(f"  {i+1}. {row['pool_name']}")
            print(f"     DEX: {row['dex']} | Price: ${row['price_usd']:.6f}")
            print(f"     Volume 24h: {format_number(row['volume_24h'])} | Liquidity: {format_number(row['liquidity_usd'])}")
            print(f"     Price Change 24h: {row['price_change_24h']:.2f}%")
            print()
        
        return df
        
    except Exception as e:
        print(f"✗ Error fetching trending pools: {e}")
        return pd.DataFrame()


def get_pools_megafilter(
    network: str = "eth",
    min_volume_24h: float = 100000,
    max_liquidity: float = 1000000,
    min_transactions: int = 100,
    limit: int = 10
) -> pd.DataFrame:
    """
    Use the Megafilter endpoint to find pools with specific characteristics.
    
    This is a PAID endpoint (Analyst plan+) that allows advanced filtering
    to find high-volume, lower-liquidity pools (higher volatility targets).
    
    Args:
        network: Network ID
        min_volume_24h: Minimum 24h volume in USD
        max_liquidity: Maximum liquidity (to find volatile pools)
        min_transactions: Minimum number of transactions
        limit: Maximum results
    
    Returns:
        DataFrame with filtered pool data
    """
    print(f"\n🔍 Using Megafilter to find high-opportunity pools on {network}...")
    
    endpoint = "/pools/megafilter"
    params = {
        "networks": network,
        "volume_24h_usd_min": min_volume_24h,
        "reserve_usd_max": max_liquidity,
        "tx_24h_count_min": min_transactions,
        "order": "volume_usd_h24_desc",
        "page": 1,
        "limit": limit
    }
    
    try:
        data = cg_request(endpoint, params)
        pools = data.get("data", [])
        
        if not pools:
            print("No pools found matching criteria. This endpoint requires a paid API plan.")
            return pd.DataFrame()
        
        pool_data = []
        for pool in pools:
            attr = pool.get("attributes", {})
            relationships = pool.get("relationships", {})
            
            pool_data.append({
                "pool_address": attr.get("address", ""),
                "pool_name": attr.get("name", "Unknown"),
                "network": relationships.get("network", {}).get("data", {}).get("id", network),
                "dex": relationships.get("dex", {}).get("data", {}).get("id", "unknown"),
                "base_token_symbol": attr.get("base_token_symbol", ""),
                "quote_token_symbol": attr.get("quote_token_symbol", ""),
                "price_usd": float(attr.get("base_token_price_usd", 0) or 0),
                "volume_24h": float(attr.get("volume_usd", {}).get("h24", 0) or 0),
                "liquidity_usd": float(attr.get("reserve_in_usd", 0) or 0),
                "volume_liquidity_ratio": 0,  # Will calculate
                "transactions_24h": int(attr.get("transactions", {}).get("h24", {}).get("buys", 0) or 0) +
                                   int(attr.get("transactions", {}).get("h24", {}).get("sells", 0) or 0)
            })
        
        df = pd.DataFrame(pool_data)
        
        # Calculate volume-to-liquidity ratio (higher = more volatile)
        df["volume_liquidity_ratio"] = df["volume_24h"] / df["liquidity_usd"].replace(0, 1)
        
        print(f"✓ Found {len(df)} pools matching criteria")
        return df
        
    except Exception as e:
        print(f"✗ Error with Megafilter (may require paid plan): {e}")
        return pd.DataFrame()


# =============================================================================
# STEP 2: Find Profitable Wallets in a Pool
# =============================================================================
def get_pool_trades(network: str, pool_address: str, limit: int = 300) -> pd.DataFrame:
    """
    Fetch recent trades from a specific pool to analyze wallet performance.
    
    Uses the /onchain/networks/{network}/pools/{pool_address}/trades endpoint.
    
    Args:
        network: Network ID
        pool_address: Pool contract address
        limit: Number of trades to fetch (max 300 per call)
    
    Returns:
        DataFrame with trade data
    """
    print(f"\n📈 Fetching trades for pool {pool_address[:10]}...")
    
    endpoint = f"/networks/{network}/pools/{pool_address}/trades"
    params = {"limit": min(limit, 300)}
    
    try:
        data = cg_request(endpoint, params)
        trades = data.get("data", [])
        
        if not trades:
            print("No trades found for this pool.")
            return pd.DataFrame()
        
        trade_data = []
        for trade in trades:
            attr = trade.get("attributes", {})
            
            trade_data.append({
                "tx_hash": attr.get("tx_hash", ""),
                "block_timestamp": attr.get("block_timestamp", ""),
                "tx_from_address": attr.get("tx_from_address", ""),
                "kind": attr.get("kind", ""),  # 'buy' or 'sell'
                "volume_usd": float(attr.get("volume_in_usd", 0) or 0),
                "from_token_amount": float(attr.get("from_token_amount", 0) or 0),
                "to_token_amount": float(attr.get("to_token_amount", 0) or 0),
                "price_from_in_usd": float(attr.get("price_from_in_usd", 0) or 0),
                "price_to_in_usd": float(attr.get("price_to_in_usd", 0) or 0),
            })
        
        df = pd.DataFrame(trade_data)
        print(f"✓ Fetched {len(df)} trades")
        return df
        
    except Exception as e:
        print(f"✗ Error fetching trades: {e}")
        return pd.DataFrame()


def analyze_wallet_profitability(trades_df: pd.DataFrame, min_trades: int = 3) -> pd.DataFrame:
    """
    Analyze wallet profitability based on trade history.
    
    Calculates realized PnL for each wallet by analyzing their buy and sell patterns.
    
    Args:
        trades_df: DataFrame of trades from get_pool_trades()
        min_trades: Minimum number of trades to consider a wallet
    
    Returns:
        DataFrame with wallet profitability metrics
    """
    if trades_df.empty:
        return pd.DataFrame()
    
    print("\n📊 Analyzing wallet profitability...")
    
    # Group trades by wallet
    wallet_stats = []
    
    for wallet, group in trades_df.groupby("tx_from_address"):
        if len(group) < min_trades:
            continue
        
        buys = group[group["kind"] == "buy"]
        sells = group[group["kind"] == "sell"]
        
        total_bought = buys["volume_usd"].sum()
        total_sold = sells["volume_usd"].sum()
        
        # Simple realized PnL calculation
        realized_pnl = total_sold - total_bought
        
        # Calculate win rate (profitable trades)
        # Note: This is a simplified calculation
        avg_buy_price = buys["price_to_in_usd"].mean() if len(buys) > 0 else 0
        avg_sell_price = sells["price_from_in_usd"].mean() if len(sells) > 0 else 0
        
        wallet_stats.append({
            "wallet_address": wallet,
            "total_trades": len(group),
            "buys": len(buys),
            "sells": len(sells),
            "total_bought_usd": total_bought,
            "total_sold_usd": total_sold,
            "realized_pnl_usd": realized_pnl,
            "avg_trade_size_usd": group["volume_usd"].mean(),
            "first_trade": group["block_timestamp"].min(),
            "last_trade": group["block_timestamp"].max(),
        })
    
    df = pd.DataFrame(wallet_stats)
    
    if df.empty:
        print("No wallets with sufficient trade history found.")
        return df
    
    # Sort by realized PnL
    df = df.sort_values("realized_pnl_usd", ascending=False)
    
    print(f"✓ Analyzed {len(df)} wallets with {min_trades}+ trades")
    print("\n🏆 Top Profitable Wallets:")
    print("-" * 80)
    
    for i, row in df.head(5).iterrows():
        pnl_emoji = "🟢" if row["realized_pnl_usd"] > 0 else "🔴"
        print(f"  {pnl_emoji} Wallet: {row['wallet_address'][:10]}...{row['wallet_address'][-6:]}")
        print(f"     Trades: {row['total_trades']} ({row['buys']} buys, {row['sells']} sells)")
        print(f"     Realized PnL: ${row['realized_pnl_usd']:,.2f}")
        print(f"     Avg Trade Size: ${row['avg_trade_size_usd']:,.2f}")
        print()
    
    return df


def find_profitable_wallets(
    network: str = "eth",
    pool_address: str = None,
    min_trades: int = 3,
    min_pnl: float = 100
) -> list:
    """
    Complete workflow to find profitable wallets in a pool.
    
    Args:
        network: Network ID
        pool_address: Pool to analyze
        min_trades: Minimum trades per wallet
        min_pnl: Minimum PnL to consider
    
    Returns:
        List of profitable wallet addresses
    """
    if not pool_address:
        print("✗ Pool address required")
        return []
    
    # Get recent trades
    trades_df = get_pool_trades(network, pool_address)
    
    if trades_df.empty:
        return []
    
    # Analyze wallet profitability
    wallets_df = analyze_wallet_profitability(trades_df, min_trades)
    
    if wallets_df.empty:
        return []
    
    # Filter profitable wallets
    profitable = wallets_df[wallets_df["realized_pnl_usd"] >= min_pnl]
    
    print(f"\n✓ Found {len(profitable)} wallets with PnL >= ${min_pnl}")
    
    return profitable["wallet_address"].tolist()


# =============================================================================
# STEP 3: Real-Time Trade Detection via WebSocket
# =============================================================================
async def subscribe_to_pool_trades(
    pool_address: str,
    network: str = "eth",
    callback=None,
    duration_seconds: int = 60
):
    """
    Subscribe to real-time trades for a pool using CoinGecko WebSocket.
    
    This is a PAID feature (Analyst plan+) that provides sub-second latency
    for trade detection - crucial for copy trading speed.
    
    Args:
        pool_address: Pool address to monitor
        network: Network ID
        callback: Function to call when trade is detected
        duration_seconds: How long to listen
    """
    import websockets
    
    ws_url = f"wss://ws-onchain.coingecko.com/onchain/v1/subscribe/trades"
    
    print(f"\n🔌 Connecting to CoinGecko WebSocket...")
    print(f"   Monitoring pool: {pool_address[:10]}...")
    print(f"   Duration: {duration_seconds} seconds")
    print("-" * 50)
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # Subscribe message
            subscribe_msg = {
                "action": "subscribe",
                "params": {
                    "pool_addresses": [pool_address],
                    "network": network
                },
                "api_key": API_KEY
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            print("✓ Subscribed to trade stream")
            
            # Listen for trades
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=5.0
                    )
                    
                    data = json.loads(message)
                    
                    if data.get("type") == "trade":
                        print(f"\n🔔 TRADE DETECTED!")
                        print(f"   TX Hash: {data.get('tx_hash', 'N/A')}")
                        print(f"   Type: {data.get('kind', 'N/A')}")
                        print(f"   Volume: ${data.get('volume_usd', 0):,.2f}")
                        
                        if callback:
                            await callback(data)
                    
                except asyncio.TimeoutError:
                    # No message received, continue listening
                    pass
                except Exception as e:
                    print(f"Error processing message: {e}")
            
            print("\n✓ WebSocket monitoring completed")
            
    except Exception as e:
        print(f"✗ WebSocket connection failed: {e}")
        print("  Note: WebSocket requires paid Analyst plan or above")


# =============================================================================
# STEP 4: Copy Trade Execution Logic
# =============================================================================
def verify_transaction(tx_hash: str) -> dict:
    """
    Verify transaction details using Blockscout API.
    
    Gets the 'from' address to check if it matches our target wallets.
    
    Args:
        tx_hash: Transaction hash to verify
    
    Returns:
        Transaction details including from address
    """
    url = f"{BLOCKSCOUT_BASE_URL}/transactions/{tx_hash}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            "tx_hash": tx_hash,
            "from_address": data.get("from", {}).get("hash", ""),
            "to_address": data.get("to", {}).get("hash", ""),
            "value": data.get("value", "0"),
            "status": data.get("status", ""),
            "block_number": data.get("block", 0),
            "timestamp": data.get("timestamp", ""),
        }
        
    except Exception as e:
        print(f"✗ Error verifying transaction: {e}")
        return {}


class PaperTradingEngine:
    """
    Simulated trading engine for copy trading.
    
    This implements proportional allocation - sizing trades as a percentage
    of the follower's equity rather than absolute mirror amounts.
    
    In production, this would integrate with a DEX to execute real trades.
    """
    
    def __init__(self, initial_equity: float = 10000.0, max_position_pct: float = 0.1):
        """
        Initialize paper trading engine.
        
        Args:
            initial_equity: Starting portfolio value in USD
            max_position_pct: Maximum position size as % of equity
        """
        self.equity = initial_equity
        self.max_position_pct = max_position_pct
        self.positions = {}
        self.trades = []
        self.target_wallets = set()
        
        print(f"\n💰 Paper Trading Engine Initialized")
        print(f"   Starting Equity: ${self.equity:,.2f}")
        print(f"   Max Position Size: {self.max_position_pct * 100}%")
    
    def add_target_wallet(self, wallet_address: str):
        """Add a wallet to the copy trade target list."""
        self.target_wallets.add(wallet_address.lower())
        print(f"   ✓ Added target wallet: {wallet_address[:10]}...")
    
    def calculate_position_size(self, leader_trade_usd: float) -> float:
        """
        Calculate proportional position size.
        
        Instead of mirroring exact amounts, we calculate a proportional
        size based on our equity and risk parameters.
        """
        max_size = self.equity * self.max_position_pct
        
        # Use the smaller of max size or a scaled version of leader's trade
        # This prevents over-leveraging on large leader trades
        position_size = min(max_size, leader_trade_usd * 0.1)  # 10% of leader size
        
        return round(position_size, 2)
    
    def check_slippage(
        self,
        current_price: float,
        entry_price: float,
        max_slippage_pct: float = 2.0
    ) -> bool:
        """
        Check if current price is within acceptable slippage.
        
        Prevents buying at peaks if the target wallet already pumped the price.
        """
        if entry_price == 0:
            return False
        
        slippage = abs(current_price - entry_price) / entry_price * 100
        
        if slippage > max_slippage_pct:
            print(f"   ⚠ Slippage too high: {slippage:.2f}% > {max_slippage_pct}%")
            return False
        
        return True
    
    async def execute_copy_trade(self, trade_data: dict):
        """
        Execute a copy trade based on detected trade.
        
        Workflow:
        1. Receive trade event from WebSocket
        2. Verify transaction using Blockscout
        3. Check if from_address matches target wallets
        4. If match, execute proportional trade
        """
        tx_hash = trade_data.get("tx_hash", "")
        
        if not tx_hash:
            return
        
        # Verify transaction
        print(f"\n🔍 Verifying transaction {tx_hash[:10]}...")
        tx_info = verify_transaction(tx_hash)
        
        if not tx_info:
            print("   ✗ Could not verify transaction")
            return
        
        from_address = tx_info.get("from_address", "").lower()
        
        # Check if this is from a target wallet
        if from_address not in self.target_wallets:
            print(f"   ℹ Trade from {from_address[:10]}... not in target list")
            return
        
        print(f"   ✓ MATCH! Target wallet trade detected!")
        
        # Calculate position size
        leader_volume = float(trade_data.get("volume_usd", 0))
        position_size = self.calculate_position_size(leader_volume)
        
        # Get trade details
        trade_kind = trade_data.get("kind", "unknown")
        token_symbol = trade_data.get("base_token_symbol", "TOKEN")
        current_price = float(trade_data.get("price_usd", 0))
        
        # Execute paper trade
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "tx_hash": tx_hash,
            "copied_wallet": from_address,
            "action": trade_kind,
            "token": token_symbol,
            "amount_usd": position_size,
            "price": current_price,
            "leader_volume_usd": leader_volume,
            "status": "EXECUTED (PAPER)"
        }
        
        self.trades.append(trade_record)
        
        # Update positions
        if trade_kind == "buy":
            self.equity -= position_size
            current_qty = self.positions.get(token_symbol, 0)
            if current_price > 0:
                new_qty = position_size / current_price
                self.positions[token_symbol] = current_qty + new_qty
        elif trade_kind == "sell":
            token_qty = self.positions.get(token_symbol, 0)
            if token_qty > 0:
                sell_value = min(position_size, token_qty * current_price)
                self.equity += sell_value
                self.positions[token_symbol] = max(0, token_qty - (sell_value / max(current_price, 0.0001)))
        
        print(f"\n📝 PAPER TRADE EXECUTED:")
        print(f"   Action: {trade_kind.upper()}")
        print(f"   Token: {token_symbol}")
        print(f"   Amount: ${position_size:,.2f}")
        print(f"   Price: ${current_price:.6f}")
        print(f"   Leader traded: ${leader_volume:,.2f}")
        print(f"   Remaining equity: ${self.equity:,.2f}")
    
    def get_summary(self):
        """Print trading summary."""
        print("\n" + "=" * 60)
        print("📊 PAPER TRADING SUMMARY")
        print("=" * 60)
        print(f"Total Trades Executed: {len(self.trades)}")
        print(f"Current Equity: ${self.equity:,.2f}")
        print(f"\nOpen Positions:")
        
        for token, qty in self.positions.items():
            if qty > 0:
                print(f"   {token}: {qty:.6f}")
        
        if self.trades:
            print(f"\nRecent Trades:")
            for trade in self.trades[-5:]:
                print(f"   [{trade['timestamp']}] {trade['action'].upper()} "
                      f"${trade['amount_usd']:.2f} {trade['token']}")


# =============================================================================
# Main Execution
# =============================================================================
def main():
    """
    Main execution flow demonstrating the complete copy trading bot.
    """
    print("=" * 60)
    print("🤖 HIGH-FREQUENCY CRYPTO COPY TRADING BOT")
    print("=" * 60)
    print("\n⚠️  DISCLAIMER: This is for educational purposes only.")
    print("    Not financial advice. Use at your own risk.\n")
    
    # -------------------------------------------------------------------------
    # STEP 1: Find profitable tokens and pools
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 1: DISCOVERING PROFITABLE POOLS")
    print("=" * 60)
    
    # Use trending pools (free endpoint)
    trending_pools = get_trending_pools(network="eth", limit=10)
    
    if trending_pools.empty:
        # Try with a different network
        trending_pools = get_trending_pools(network="base", limit=10)
    
    # Select the top pool for analysis
    if not trending_pools.empty:
        target_pool = trending_pools.iloc[0]
        pool_address = target_pool["pool_address"]
        pool_network = "eth"  # Default network
        
        print(f"\n🎯 Selected Pool for Analysis:")
        print(f"   {target_pool['pool_name']}")
        print(f"   Address: {pool_address}")
    else:
        # Use a known active pool as fallback (Ethereum PEPE/WETH on Uniswap V2)
        pool_address = "0xa43fe16908251ee70ef74718545e4fe6c5ccec9f"
        pool_network = "eth"
        print(f"\n🎯 Using fallback pool: {pool_address[:20]}...")
    
    # -------------------------------------------------------------------------
    # STEP 2: Find profitable wallets
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 2: ANALYZING WALLET PROFITABILITY")
    print("=" * 60)
    
    profitable_wallets = find_profitable_wallets(
        network=pool_network,
        pool_address=pool_address,
        min_trades=2,
        min_pnl=50
    )
    
    # -------------------------------------------------------------------------
    # STEP 3 & 4: Set up copy trading (demonstration)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 3 & 4: COPY TRADING SETUP")
    print("=" * 60)
    
    # Initialize paper trading engine
    trader = PaperTradingEngine(initial_equity=10000.0, max_position_pct=0.05)
    
    # Add profitable wallets as targets
    if profitable_wallets:
        for wallet in profitable_wallets[:3]:  # Top 3 wallets
            trader.add_target_wallet(wallet)
    else:
        # Add demo target for illustration
        print("\n   ℹ No profitable wallets found, adding demo target")
        trader.add_target_wallet("0x" + "1" * 40)
    
    # -------------------------------------------------------------------------
    # WebSocket Demo (requires paid plan)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("WEBSOCKET REAL-TIME MONITORING")
    print("-" * 60)
    print("\n⚠️  Note: Real-time WebSocket monitoring requires CoinGecko Analyst plan.")
    print("    The bot would listen for trades and execute copies in real-time.")
    print("\n    To enable real-time monitoring:")
    print("    1. Upgrade to CoinGecko Analyst plan")
    print("    2. Uncomment the WebSocket code below")
    print("    3. Run: asyncio.run(subscribe_to_pool_trades(pool_address, callback=trader.execute_copy_trade))")
    
    # Uncomment to enable real-time monitoring (requires paid plan):
    # async def run_websocket():
    #     await subscribe_to_pool_trades(
    #         pool_address=pool_address,
    #         network=pool_network,
    #         callback=trader.execute_copy_trade,
    #         duration_seconds=300  # Monitor for 5 minutes
    #     )
    # asyncio.run(run_websocket())
    
    # Print summary
    trader.get_summary()
    
    print("\n" + "=" * 60)
    print("✅ COPY TRADING BOT DEMONSTRATION COMPLETE")
    print("=" * 60)
    print("\n🔗 Get started with CoinGecko API:")
    print("   https://www.coingecko.com/en/api/pricing")
    print("\n📚 Documentation:")
    print("   https://docs.coingecko.com")


if __name__ == "__main__":
    main()
