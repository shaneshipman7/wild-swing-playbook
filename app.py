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

# CRITICAL: Custom CSS Injector to maximize text contrast in metric cards
st.markdown("""
    <style>
        /* Force dark background for the main canvas */
        .main { background-color: #020617 !important; }
        
        /* High-contrast container styles for top metrics */
        div[data-testid="stMetric"] {
            background-color: #0f172a !important; 
            padding: 20px !important; 
            border-radius: 14px !important; 
            border: 2px solid #1e293b !important;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        
        /* Force metric Top Label to be Crisp, Readable Light Grey/White */
        div[data-testid="stMetricLabel"] > div {
            color: #f1f5f9 !important;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em !important;
            text-transform: uppercase !important;
        }
        
        /* Force metric Big Number Value to be High-Contrast Bright Teal/White */
        div[data-testid="stMetricValue"] > div {
            color: #2dd4bf !important;
            font-size: 2.25rem !important;
            font-weight: 900 !important;
        }
        
        /* Format Subtext/Delta colors strictly if present */
        div[data-testid="stMetricDelta"] {
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("⚠️ *Educational & Technical Analysis Only — Not financial advice. Trading involves substantial risk of loss.*")
st.markdown("---")

# ====================================================================
# 2. ONLINE LIVE DATA STREAMING & PARSING ENGINE
# ====================================================================
@st.cache_data(ttl=30)
def stream_playbook_from_web():
    """Streams the raw CSV directly from the online GitHub URL into memory."""
    online_url = "https://raw.githubusercontent.com/shaneshipman7/wild-swing-playbook/main/Master_Playbook_Database_2026-06-05.csv"
    
    try:
        df = pd.read_csv(online_url)
        
        # Strip invisible whitespace characters from headers
        df.columns = df.columns.str.strip()
        
        df = df[df['Ticker'].notna()]
        df = df[df['Ticker'] != 'EXPERIMENTAL DATA ONLY']
        df['Ticker'] = df['Ticker'].str.strip().str.upper()
        
        if 'Scenario' in df.columns:
            df['Scenario'] = df['Scenario'].str.strip()
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='Date', ascending=False)
        
        # --- CRITICAL DEDUPLICATION MATRIX ---
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
refresh_speed = st.sidebar.slider("Live Market Pricing Loop (Seconds)", min_value=5, max_value=60, value=15)

dashboard_anchor = st.empty()

# ====================================================================
# 4. RUNTIME INFINITE LIVE MARKET LOOP
# ====================================================================
while True:
    base_playbook = stream_playbook_from_web()
    
    if base_playbook.empty:
        with dashboard_anchor.container():
            st.warning("🔄 Re-establishing cloud connection to online database file...")
        time.sleep(5)
        continue
        
    working_df = base_playbook.copy()
    unique_tickers = list(working_df['Ticker'].unique())
    
    # --- LIVE BATCH PRICE FETCHER ---
    live_prices = {}
    if unique_tickers:
        try:
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
    # 5. FIXED DATA ALIGNMENT & EXTRACTION MAP
    # ====================================================================
    working_df['Live Price'] = working_df['Ticker'].map(live_prices).apply(lambda x: round(x, 2) if pd.notna(x) else None)
    
    # Direct Fallback mappings to match columns regardless of spacing
    working_df['🔑 Entry Zone'] = working_df['Entry'].fillna('Pending Sync') if 'Entry' in working_df.columns else 'N/A'
    working_df['🛡️ Stop Loss'] = working_df['Stop_Loss'].fillna('Not Set') if 'Stop_Loss' in working_df.columns else 'N/A'
    
    # Target Alignment
    if 'Targets' in working_df.columns:
        working_df['🎯 Target Objectives'] = working_df['Targets'].fillna('Not Set')
    elif 'Target' in working_df.columns:
        working_df['🎯 Target Objectives'] = working_df['Target'].fillna('Not Set')
    else:
        working_df['🎯 Target Objectives'] = 'Not Set'
    
    # Risk Reward Linkage
    rr_variants = ['R_R_Ratio', 'R:R Ratio', 'Risk_Reward', 'R:R']
    found_rr = next((col for col in rr_variants if col in working_df.columns), None)
    working_df['⚖️ Risk:Reward'] = working_df[found_rr].fillna('N/A') if found_rr else 'N/A'
        
    # Probability Isolation (Keeps it distinct from R:R)
    prob_variants = ['Est_Probability', 'Est_Prob', 'Probability', 'Est. Probability']
    found_prob = next((col for col in prob_variants if col in working_df.columns), None)
    working_df['📊 Est. Prob.'] = working_df[found_prob].fillna('N/A') if found_prob else 'N/A'
    
    # Direct TradingView Link Builder
    working_df['TradingView Chart'] = working_df['Ticker'].apply(
        lambda t: f"https://www.tradingview.com/symbols/{t.upper()}/" if t != 'MULTI' else ""
    )

    # ====================================================================
    # 6. GRAPHICAL USER INTERFACE RENDERING
    # ====================================================================
    with dashboard_anchor.container():
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(label="Total Active Setup Records", value=len(working_df))
        with m2:
            st.metric(label="Unique Monitored Assets", value=working_df['Ticker'].nunique())
        with m3:
            st.metric(label="Cloud Stream State", value="● ACTIVE", delta=f"{refresh_speed}s interval")
            
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        
        # Enforcing final physical presentation order
        final_column_layout = [
            'Ticker', 'Scenario', 'Live Price', '🔑 Entry Zone', 
            '🛡️ Stop Loss', '🎯 Target Objectives', '⚖️ Risk:Reward', '📊 Est. Prob.', 'TradingView Chart'
        ]
        
        active_cols = [c for c in final_column_layout if c in working_df.columns]
        display_df = working_df[active_cols]

        st.dataframe(
            display_df,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Scenario": st.column_config.TextColumn("Strategy Scenario", width="large"),
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
                "⚖️ Risk:Reward": st.column_config.TextColumn("R:R Ratio", width="small"),
                "📊 Est. Prob.": st.column_config.TextColumn("Est. Probability", width="small"),
                "TradingView Chart": st.column_config.LinkColumn("Chart Link", display_text="TradingView ↗")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.caption(f"Last Live System Pulse: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    time.sleep(refresh_speed)
