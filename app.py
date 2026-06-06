import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# ====================================================================
# 1. PAGE SETUP & CLEAN DARK THEME CONFIG
# ====================================================================
st.set_page_config(
    page_title="Wild Swing Trades • Live Playbook",
    page_icon="📈",
    layout="wide"
)

# This forces the app into a dark mode style sheet natively without needing external files
st.markdown("""
    <style>
        /* Force background color */
        .main, [data-testid="stAppViewContainer"] { 
            background-color: #020617 !important; 
        }
        
        /* Force ALL text to be high-contrast bright white */
        h1, h2, h3, p, span, label, li, div {
            color: #ffffff !important;
        }
        
        /* Metric Card Backgrounds */
        div[data-testid="stMetric"] {
            background-color: #0f172a !important; 
            padding: 20px !important; 
            border-radius: 12px !important; 
            border: 1px solid #1e293b !important;
        }
        
        /* Metric Values (Large Numbers) Highlighted Cyan */
        div[data-testid="stMetricValue"] div, 
        div[data-testid="stMetricValue"] span {
            color: #2dd4bf !important;
            font-weight: 800 !important;
        }
        
        /* Table / Dataframe font colors */
        .stDataFrame div, .stDataFrame span, .stDataFrame th, .stDataFrame td {
            color: #ffffff !important;
        }
        
        /* Soften the disclaimer text */
        .disclaimer {
            color: #94a3b8 !important;
            font-style: italic;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("<p class='disclaimer'>⚠️ Educational & Technical Analysis Only — Not financial advice. Trading involves risk.</p>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================================
# 2. DATA LOADING ENGINE (ANTI-BUG IMMUNITY)
# ====================================================================
@st.cache_data(ttl=30)
def load_playbook_safely():
    url = "https://raw.githubusercontent.com/shaneshipman7/wild-swing-playbook/main/Master_Playbook_Database_2026-06-05.csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # Eliminate empty rows and drop old experimental markers
        df = df[df['Ticker'].notna()]
        df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()
        df = df[df['Ticker'] != 'EXPERIMENTAL DATA ONLY']
        
        # AUTOMATIC FIREWALL: Only accepts rows where the Ticker is a real 1-5 letter symbol.
        # This completely drops 'MULTI' out of the loop so it can't corrupt your pricing!
        df = df[df['Ticker'].str.match(r'^[A-Z]{1,5}$')]
        
        return df
    except Exception as e:
        st.error(f"Database Sync Pending: {e}")
        return pd.DataFrame()

# Sidebar fallback loop controller
refresh_speed = st.sidebar.slider("Refresh Loop Interval (Seconds)", 5, 60, 15)
dashboard_container = st.empty()

# ====================================================================
# 3. LIVE MARKET RUNTIME LOOP
# ====================================================================
while True:
    raw_data = load_playbook_safely()
    
    if raw_data.empty:
        time.sleep(5)
        continue
        
    working_df = raw_data.copy()
    tickers_list = list(working_df['Ticker'].unique())
    
    # Live Price Batch Retrieval
    live_prices = {}
    if tickers_list:
        try:
            market_data = yf.download(" ".join(tickers_list), period="1d", interval="1m", group_by='ticker', progress=False)
            for ticker in tickers_list:
                try:
                    if len(tickers_list) == 1:
                        live_prices[ticker] = market_data['Close'].iloc[-1]
                    else:
                        live_prices[ticker] = market_data[ticker]['Close'].iloc[-1]
                except:
                    live_prices[ticker] = None
        except:
            pass
            
    # Direct Map & Structural Fallbacks
    working_df['Live Price'] = working_df['Ticker'].map(live_prices).round(2)
    working_df['Entry Zone'] = working_df['Entry'].fillna('Pending')
    working_df['Stop Loss'] = working_df['Stop_Loss'].fillna('Not Set')
    working_df['Targets'] = working_df['Targets'].fillna('Not Set')
    
    # UN-SWAPPED FIX: Pulls data strictly by your raw database layout designations
    working_df['Risk:Reward'] = working_df['R_R_Ratio'].fillna('N/A')
    working_df['Est. Probability'] = working_df['Est_Probability'].fillna('N/A')
    
    # Live TradingView Chart URL Generator
    working_df['Chart Link'] = working_df['Ticker'].apply(lambda t: f"https://www.tradingview.com/symbols/{t}/")

    # ====================================================================
    # 4. DASHBOARD PRESENTATION LAYOUT
    # ====================================================================
    with dashboard_container.container():
        # Clean Metric Display Blocks
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Active Setups", len(working_df))
        m2.metric("Unique Monitored Assets", working_df['Ticker'].nunique())
        m3.metric("Stream Pulse Status", "● ONLINE", f"{refresh_speed}s interval")
        
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        
        # Build the table grid arrangement explicitly
        intended_columns = ['Ticker', 'Scenario', 'Live Price', 'Entry Zone', 'Stop Loss', 'Targets', 'Risk:Reward', 'Est. Probability', 'Chart Link']
        available_display_cols = [col for col in intended_columns if col in working_df.columns]
        display_output_df = working_df[available_display_cols]
        
        st.dataframe(
            display_output_df,
            column_config={
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
                "Chart Link": st.column_config.LinkColumn("Chart Link", display_text="TradingView ↗")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.caption(f"System Heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    time.sleep(refresh_speed)
