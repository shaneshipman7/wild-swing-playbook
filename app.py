import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# ====================================================================
# 1. PAGE SETUP & INTERFACE LAYOUT
# ====================================================================
st.set_page_config(
    page_title="Wild Swing Trades • Live Playbook",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for clean metrics and layout
st.markdown("""
    <style>
        .reportview-container { background: #020617; }
        .stMetric { background-color: #0f172a; padding: 15px; border-radius: 12px; border: 1px solid #1e293b; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("⚠️ *Educational & Technical Analysis Only — Not financial advice. Trading involves substantial risk of loss.*")
st.markdown("---")

# ====================================================================
# 2. ONLINE LIVE DATA STREAMING & PARSING ENGINE
# ====================================================================
@st.cache_data(ttl=30)  # Dynamic 30-second memory threshold to catch online file edits
def stream_playbook_from_web():
    """Streams the raw CSV directly from the online GitHub URL into memory."""
    # Direct raw text server endpoint to bypass GitHub's web interface container
    online_url = "https://raw.githubusercontent.com/shaneshipman7/wild-swing-playbook/main/Master_Playbook_Database_2026-06-05.csv"
    
    try:
        # Pull the dataset over a live HTTPS data stream
        df = pd.read_csv(online_url)
        
        # Clean white space formatting issues and drop metadata placeholders
        df = df[df['Ticker'].notna()]
        df = df[df['Ticker'] != 'EXPERIMENTAL DATA ONLY']
        df['Ticker'] = df['Ticker'].str.strip().str.upper()
        df['Scenario'] = df['Scenario'].str.strip()
        
        # Standardize and sort chronologically by date if the column exists
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
        
        # --- CRITICAL DEDUPLICATION MATRIX ---
        # Group by BOTH Ticker and Scenario so distinct strategies (e.g., Pullback vs Breakout) 
        # on the exact same ticker stay active, while older duplicates are discarded.
        if 'Scenario' in df.columns:
            df = df.drop_duplicates(subset=['Ticker', 'Scenario'], keep='first')
        else:
            df = df.drop_duplicates(subset=['Ticker'], keep='first')
            
        return df
    except Exception as e:
        st.sidebar.error(f"Online Streaming Engine Offline: {e}")
        return pd.DataFrame()

# ====================================================================
# 3. SIDEBAR NAVIGATION & SPEED CONTROLS
# ====================================================================
st.sidebar.header("⚙️ Core Processing Settings")
st.sidebar.markdown("This dashboard updates completely over the web without local server folders.")
refresh_speed = st.sidebar.slider("Live Market Pricing Loop (Seconds)", min_value=5, max_value=60, value=15)

# Initialize the dynamic view container anchor
dashboard_anchor = st.empty()

# ====================================================================
# 4. RUNTIME INFINITE LIVE MARKET LOOP
# ====================================================================
while True:
    # Safely extract fresh parsed structures from the web source
    base_playbook = stream_playbook_from_web()
    
    if base_playbook.empty:
        with dashboard_anchor.container():
            st.warning("🔄 Re-establishing cloud connection to online database file...")
        time.sleep(5)
        continue
        
    # Isolate unique tickers for optimized bulk batch pricing retrieval
    working_df = base_playbook.copy()
    unique_tickers = list(working_df['Ticker'].unique())
    
    # --- LIVE BATCH PRICE FETCHER ---
    live_prices = {}
    if unique_tickers:
        try:
            # Join assets together with spaces to pass a single query to yfinance
            tickers_string = " ".join(unique_tickers)
            data = yf.download(tickers_string, period="1d", interval="1m", group_by='ticker', progress=False)
            
            for ticker in unique_tickers:
                try:
                    if len(unique_tickers) == 1:
                        live_prices[ticker] = data['Close'].iloc[-1]
                    else:
                        live_prices[ticker] = data[ticker]['Close'].iloc[-1]
                except Exception:
                    live_prices[ticker] = None
        except Exception:
            pass

    # ====================================================================
    # 5. DATA ALIGNMENT & EXTRACTION TRANSFORMATIONS
    # ====================================================================
    # Map raw live numbers back to data rows
    working_df['Live Price'] = working_df['Ticker'].map(live_prices)
    working_df['Live Price'] = working_df['Live Price'].apply(lambda x: round(x, 2) if pd.notna(x) else None)
    
    # Separate core objectives out cleanly into distinct columns
    working_df['🔑 Entry Zone'] = working_df['Entry'].fillna('Pending Sync')
    working_df['🛡️ Stop Loss'] = working_df['Stop_Loss'].fillna('Not Set')
    working_df['🎯 Target Objectives'] = working_df['Targets'].fillna('Not Set')
    
    # --- LOCKED TO TRADINGVIEW TERMINAL LINKS ---
    working_df['TradingView Chart'] = working_df['Ticker'].apply(
        lambda t: f"https://www.tradingview.com/symbols/{t.upper()}/"
    )

    # ====================================================================
    # 6. GRAPHICAL USER INTERFACE RENDERING
    # ====================================================================
    with dashboard_anchor.container():
        
        # Upper KPI Metrics Grid
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Active Setup Records", len(working_df))
        with m2:
            st.metric("Unique Monitored Assets", working_df['Ticker'].nunique())
        with m3:
            st.metric("Cloud Stream State", "● ACTIVE", delta=f"{refresh_speed}s interval")
            
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        
        # Designate layout sequence for standard table presentation columns
        final_column_layout = [
            'Ticker', 'Scenario', 'Live Price', '🔑 Entry Zone', 
            '🛡️ Stop Loss', '🎯 Target Objectives', 'R_R_Ratio', 'TradingView Chart'
        ]
        
        # Safely extract columns verified present inside the data snapshot
        active_cols = [c for c in final_column_layout if c in working_df.columns]
        display_df = working_df[active_cols]

        # Interactive grid viewer rendering with custom column rendering rules
        st.dataframe(
            display_df,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Scenario": st.column_config.TextColumn("Strategy Scenario", width="large"),
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
                "R_R_Ratio": st.column_config.TextColumn("R:R Ratio"),
                "TradingView Chart": st.column_config.LinkColumn("Chart Link", display_text="TradingView ↗")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Lower frame footer metadata tracking tag
        st.caption(f"Last Live System Pulse: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    # Hold the program thread before automatically restarting the cycle execution layout
    time.sleep(refresh_speed)
