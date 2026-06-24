import duckdb
import pandas as pd
import streamlit as st
import altair as alt

DUCKDB_PATH = "Token_data.duckdb"
TABLE_NAME = "token_status"

@st.cache_data
def load_data(db_path: str, table_name: str) -> pd.DataFrame:
    # Short-lived connection to avoid locking issues
    with duckdb.connect(db_path, read_only=True) as con:
        df = con.execute(f"SELECT * FROM {table_name}").df()
    return df

def main():
    st.title("Token Data Viewer")

    df = load_data(DUCKDB_PATH, TABLE_NAME)

    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    st.subheader("Raw table")
    st.dataframe(df, use_container_width=True)

    # Plot grad_pert vs time for different tokens
    st.subheader("Graduation % over time")

    # Allow user to choose which tokens (names) to plot
    token_options = sorted(df["name"].dropna().unique().tolist())
    selected_names = st.multiselect(
        "Select tokens to display",
        options=token_options,
        default=token_options[:5] if len(token_options) > 5 else token_options,
    )

    if selected_names:
        plot_df = (
            df[df["name"].isin(selected_names)]
            .dropna(subset=["grad_pert", "timestamp"])
            .sort_values("timestamp")
        )

        chart = (
            alt.Chart(plot_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("timestamp:T", title="Time"),
                y=alt.Y("grad_pert:Q", title="grad_pert"),
                color=alt.Color("name:N", title="Token"),
                tooltip=["name", "timestamp", "grad_pert"],
            )
            .interactive()
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Select at least one token to see the plot.")

if __name__ == "__main__":
    main()