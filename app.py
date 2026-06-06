import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# ====================================================================
# 1. PAGE SETUP & NATIVE DARK STYLE INJECTION
# ====================================================================
st.set_page_config(
    page_title="Wild Swing Trades • Live Playbook",
    page_icon="📈",
    layout="wide"
)

# High-contrast visual overrides 
st.markdown("""
    <style>
        .main, [data-testid="stAppViewContainer"] { 
            background-color: #020617 !important; 
        }
        
        h1, h2, h3, p, span, label, li, div {
            color: #ffffff !important;
        }
        
        div[data-testid="stMetric"] {
            background-color: #0f172a !important; 
            padding: 20px !important; 
            border-radius: 12px !important; 
            border: 1px solid #1e293b !important;
        }
        
        div[data-testid="stMetricValue"] div, 
        div[data-testid="stMetricValue"] span {
            color: #2dd4bf !important;
            font-weight: 800 !important;
        }
        
        .stDataFrame div, .stDataFrame span, .stDataFrame th, .stDataFrame td {
            color: #ffffff !important;
        }
        
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
# 2. DATA STREAMING ENGINE (WITH EXPLICIT MULTI BAN)
# ====================================================================
@st.cache_data(ttl=30)
def load_playbook_safely():
    url = "https://raw.githubusercontent.com/shaneshipman7/wild-swing-playbook/main/Master_Playbook_Database_2026-06-05.csv"
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        
        # Clean up empty rows
        df = df[df['Ticker'].notna()]
        df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()
        df = df[df['Ticker'] != 'EXPERIMENTAL DATA ONLY']
        
        # --- THE ULTIMATE BANHAMMER ---
        # This completely drops 'MULTI' from your data frames forever.
        df = df[df['Ticker'] != 'MULTI']
        
        return df
    except Exception as e:
        st.error(f"Database Sync Pending: {e}")
        return pd.DataFrame()

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
    
    # Live Price Batch Retrieval (Safe from non-equity tags)
    live_prices = {}
    valid_market_tickers = [t for t in tickers_list if len(t) <= 5 and t.isalpha()]
    
    if valid_market_tickers:
        try:
            market_data = yf.download(" ".join(valid_market_tickers), period="1d", interval="1m", group_by='ticker', progress=False)
            for ticker in valid_market_tickers:
                try:
                    if len(valid_market_tickers) == 1:
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
    
    # Store raw metrics before layout swap correction
    working_df['Raw_RR_Col'] = working_df['R_R_Ratio'].fillna('N/A')
    working_df['Raw_Prob_Col'] = working_df['Est_Probability'].fillna('N/A')
    
    working_df['Chart Link'] = working_df['Ticker'].apply(lambda t: f"https://www.tradingview.com/symbols/{t}/")

    # ====================================================================
    # 4. DASHBOARD PRESENTATION LAYOUT
    # ====================================================================
    with dashboard_container.container():
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Active Setups", len(working_df))
        m2.metric("Unique Monitored Assets", working_df['Ticker'].nunique())
        m3.metric("Stream Pulse Status", "● ONLINE", f"{refresh_speed}s interval")
        
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        
        # Grid layout structure sequence
        intended_columns = ['Ticker', 'Scenario', 'Live Price', 'Entry Zone', 'Stop Loss', 'Targets', 'Raw_RR_Col', 'Raw_Prob_Col', 'Chart Link']
        display_output_df = working_df[intended_columns]
        
        st.dataframe(
            display_output_df,
            column_config={
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
                # Re-aligning the layout names so data matches the columns perfectly on screen
                "Raw_RR_Col": st.column_config.TextColumn("Est. Probability", width="small"),
                "Raw_Prob_Col": st.column_config.TextColumn("R:R Ratio", width="small"),
                "Chart Link": st.column_config.LinkColumn("Chart Link", display_text="TradingView ↗")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.caption(f"System Heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    time.sleep(refresh_speed)
