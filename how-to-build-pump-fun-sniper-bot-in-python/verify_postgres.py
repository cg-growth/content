PG_DSN = "postgresql://vnegi:1qaz2wsx@localhost:5432/price_ws_stream"

conn_r = psycopg.connect(PG_DSN)

# Set the session timezone for the connection
conn_r.execute("SET TIME ZONE 'Europe/Berlin'")

df = pd.read_sql("""
    SELECT DISTINCT ON (token_address) *
    FROM price_stream
    ORDER BY token_address, last_updated_at DESC
""", conn_r)

df
