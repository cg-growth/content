import sqlite3
import pandas as pd

def rejection_breakdown(db_path="portfolio.db"):
    """Show which check is filtering out the most signals."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT reason, executed FROM signal_log", conn)

    total = len(df)
    breakdown = (
        df[df["executed"] == 0]["reason"]
        .value_counts()
        .rename_axis("reason")
        .reset_index(name="count")
    )
    breakdown["pct_of_total"] = (breakdown["count"] / total * 100).round(1)
    return total, breakdown

if __name__ == "__main__":
    total, breakdown = rejection_breakdown()
    print(f"{total} headlines scored over the period\n")
    for _, row in breakdown.iterrows():
        print(f"{row['count']:>4}  {row['pct_of_total']:>5.1f}%   {row['reason']}")
