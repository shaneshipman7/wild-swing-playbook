import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# 1. PAGE SETUP
st.set_page_config(page_title="DFW SAS Playbook Dashboard", layout="wide")
st.title("Market Monitor Playbook")

# 2. DEFINED WATCHLIST (Add your tickers here, no duplicates possible)
WATCHLIST = ["SLV", "AAPL", "MSFT", "GOOGL"]

# 3. LIVE DATA FETCHER
def get_clean_data(ticker):
    try:
        # Fetching real live data using yfinance
        asset = yf.Ticker(ticker)
        info = asset.fast_info
        
        current_price = round(info['last_price'], 2)
        prev_close = info['previous_close']
        pct_change = round(((current_price - prev_close) / prev_close) * 100, 2)
        
        return {
            "Price": current_price,
            "Change": f"{pct_change}%",
            "Status": "Live",
            "As Of": datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        # If one ticker acts up, it won't crash the whole screen
        return {
            "Price": "N/A",
            "Change": "0.0%",
            "Status": f"Error",
            "As Of": datetime.now().strftime("%H:%M:%S")
        }

# 4. SIDEBAR REFRESH CONTROL
st.sidebar.header("Dashboard Controls")
refresh_speed = st.sidebar.slider("Refresh Interval (seconds)", min_value=5, max_value=60, value=10)

# 5. THE AUTOMATIC LIVE REFRESH LOOP
# This anchor wipes and redraws the layout cleanly every loop
dashboard_anchor = st.empty()

while True:
    fresh_market_snapshot = {}
    
    for ticker in WATCHLIST:
        # Overwrites by key name, guaranteeing NO duplication loops
        fresh_market_snapshot[ticker] = get_clean_data(ticker)
        
    df = pd.DataFrame.from_dict(fresh_market_snapshot, orient='index')
    
    with dashboard_anchor.container():
        # Render dynamic visual columns for metrics
        cols = st.columns(len(df))
        for i, (ticker, row) in enumerate(df.iterrows()):
            with cols[i]:
                st.markdown(f"### {ticker}")
                st.metric(
                    label="Current Price", 
                    value=f"${row['Price']}" if row['Price'] != "N/A" else "N/A", 
                    delta=row['Change']
                )
        
        st.write("---")
        
        # Render clean overview grid
        st.subheader("Playbook Overview Grid")
        st.dataframe(df, use_container_width=True)
        st.caption(f"Last Global Dashboard Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Pauses the script, then automatically triggers a clean rerun
    time.sleep(refresh_speed)
