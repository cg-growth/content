df_pools = analyze_pools("solana", num_rows=200).head(50)
token_list = df_pools["token_add"].dropna().unique().tolist()

DB_PATH_1 = str(Path.cwd() / "token_list.duckdb")
dbw_1 = duckdb.connect(DB_PATH_1)

dbw_1.execute("DROP TABLE IF EXISTS token_list")

dbw_1.execute("""
CREATE TABLE IF NOT EXISTS token_list (
    token_address TEXT PRIMARY KEY
);
""")

# Insert tokens (ignore duplicates)
dbw_1.executemany(
    "INSERT OR IGNORE INTO token_list(token_address) VALUES (?)",
    [(t,) for t in token_list]
)

dbw_1.close()
