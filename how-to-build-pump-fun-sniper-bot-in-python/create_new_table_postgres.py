PG_DSN = "postgresql://vnegi:1qaz2wsx@localhost:5432/price_ws_stream"

conn = psycopg.connect(PG_DSN)
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS price_stream (
    channel_type TEXT,
    network_id TEXT,
    token_address TEXT,
    usd_price DOUBLE PRECISION,
    usd_price_24h_change_percentage DOUBLE PRECISION,
    usd_market_cap DOUBLE PRECISION,
    usd_24h_vol DOUBLE PRECISION,
    last_updated_at TIMESTAMPTZ
);
""")
