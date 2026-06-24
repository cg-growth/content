import requests
import streamlit as st
import streamlit_shadcn_ui as ui

from utils import parse_ohlcv_data, plot_ohlcv, plot_price_change, plot_transaction_types, get_top_changes, process_data

# Constantss
API_BASE_URL = "https://pro-api.coingecko.com/api/v3/onchain"
NEW_POOLS_ENDPOINT = "/networks/new_pools?page=1"
TOKENS_ENDPOINT = "/tokens/info_recently_updated"
HEADERS = {"accept": "application/json", "x-cg-pro-api-key": "APIKEY"}
PLACEHOLDER_IMAGE_URL = "https://via.placeholder.com/200x200.png?text=Crypto+Icon"
st.set_option('deprecation.showPyplotGlobalUse', False)

# Set the page to wide mode
st.set_page_config(layout="wide")


@st.cache_data
def fetch_networks_data():
    url = "https://pro-api.coingecko.com/api/v3/onchain/networks?page=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        networks = response.json()["data"]
        return {network["attributes"]["name"]: network["id"] for network in networks}
    else:
        st.error(
            f"Failed to retrieve networks data. Status code: {response.status_code}"
        )
        return {}


# Modify the fetch_ohlcv_data function to accept an interval parameter
@st.cache_data
def fetch_ohlcv_data(network_id, pool_id, interval="hour"):
    url = f"https://pro-api.coingecko.com/api/v3/onchain/networks/{network_id}/pools/{pool_id}/ohlcv/{interval}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to retrieve OHLCV data. Status code: {response.status_code}")
        return []


# Function to fetch data from the API
@st.cache_data
def fetch_data(endpoint):
    url = f"{API_BASE_URL}{endpoint}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f'Failed to retrieve data from {url}. Status code: {response.status_code}')
        return None


def page_one():
    st.title('Cryptocurrency Pool Data Viewer - Page 1')
    trigger_btn = ui.button(text="Trigger Button", key="trigger_btn")
    ui.alert_dialog(show=trigger_btn, title="Alert Dialog", description="This is an alert dialog", confirm_label="OK", cancel_label="Cancel", key="alert_dialog1")
    # Main app code
    st.title('Cryptocurrency Pool Data Viewer')

    # Fetch and process data
    raw_data = fetch_data(NEW_POOLS_ENDPOINT)
    if raw_data:
        df = process_data(raw_data)

        top_volume_changes = get_top_changes(df, 'price_change_percentage_h1')

        # Display the top 3 price changes
        st.subheader('⭐️ Top 3 Pairs by 1-Hour Price Change')
        columns = st.columns(3)  # Create three columns for the top 3 changes
        for index, (col, row) in enumerate(zip(columns, top_volume_changes.iterrows())):
            with col:
                st.metric(label=row[1]['name'], value=f"{row[1]['price_change_percentage_h1']:.2f}%")
                st.text(f"Buys in last hour: {row[1]['transactions_h1_buys']}")
                st.text(f"Sells in last hour: {row[1]['transactions_h1_sells']}")


        # Create two columns for the data table and the bar chart
        col1, col2 = st.columns(2)

        with col1:
            # Display data table in the first column
            st.subheader('🏓 Data Overview')
            st.write("", df)

        with col2:
            # Visualization: Bar Chart for Price Change Percentage in the second column
            st.subheader("📊 Price Change Percentage (24h)")
            if 'price_change_percentage_h1' in df.columns:
                fig_price_change = plot_price_change(df)
                st.pyplot(fig_price_change)


def page_two():
    st.title("Crypto Liquidity Pool - OHLCV Chart")

    # Fetch networks data and populate the dropdown
    networks_data = fetch_networks_data()
    selected_network = st.selectbox("Select a network:", list(networks_data.keys()))

    # Use the selected network's ID for downstream tasks
    network_id = networks_data[selected_network]
    st.write(f"You have selected the network with ID: {network_id}")

    # Fetch pools data for the selected network
    pools_data = fetch_data(f"/networks/{network_id}/pools?page=1")
    if pools_data:

        print(pools_data)
        # Extract pool names and IDs, and use only the part after the underscore for the ID
        try:
            pool_options = {
                pool["attributes"]["name"]: pool["id"].split("_")[-1]
                for pool in pools_data["data"]
            }

        except:
            pool_options = {
                pool["attributes"]["name"]: pool["id"].split("_")[0]
                for pool in pools_data["data"]
            }

        print(pool_options)

        # Create two columns for the pool and interval dropdowns
        col_pool, col_interval = st.columns([3, 1])

        with col_pool:
            # Create a dropdown for pool names
            selected_pool_name = st.selectbox(
                "Select a pool:", list(pool_options.keys())
            )

        with col_interval:
            # Create a dropdown for OHLCV interval selection
            ohlcv_interval = st.selectbox(
                "Select interval:", ["day", "hour", "minute"], index=1
            )

        # Get the selected pool ID using the selected pool name
        selected_pool_id = pool_options[selected_pool_name]

        # Fetch and parse the OHLCV data using the selected pool ID and interval
        ohlcv_response = fetch_ohlcv_data(network_id, selected_pool_id, ohlcv_interval)
        if ohlcv_response:
            df_ohlcv, metadata = parse_ohlcv_data(ohlcv_response)
            # Use metadata as needed, for example:
            st.write("Base Token:", metadata["base"]["name"])
            st.write("Quote Token:", metadata["quote"]["name"])
            fig = plot_ohlcv(df_ohlcv)
            st.pyplot(fig)


# Sidebar navigation
st.sidebar.title('Navigation')
page = st.sidebar.radio('Select a page:', ['Page 1', 'Page 2'])

if page == 'Page 1':
    page_one()
elif page == "Page 2":
    page_two()
