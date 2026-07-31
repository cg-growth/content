DB_PATH_1 = str(Path.cwd() / "token_list.duckdb")
dbw_1 = duckdb.connect(DB_PATH_1)

tokens = dbw_1.execute("SELECT token_address FROM token_list").fetchall()
token_list = [t[0] for t in tokens]

dbw_1.close()
