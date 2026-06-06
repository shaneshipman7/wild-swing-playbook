import streamlit as st
import pandas as pd
import yfinance as yf
import time
import re
from datetime import datetime

# ====================================================================
# 1. PAGE SETUP & NATIVE COMPACT STYLE INJECTION
# ====================================================================
st.set_page_config(
    page_title="Wild Swing Trades • Live Playbook",
    page_icon="📈",
    layout="wide"
)

# Custom style tweaks to compress viewports and remove ghost toolbars
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
            padding: 12px !important; 
            border-radius: 8px !important; 
            border: 1px solid #1e293b !important;
        }
        div[data-testid="stMetricValue"] div, 
        div[data-testid="stMetricValue"] span {
            color: #2dd4bf !important;
            font-weight: 800 !important;
        }
        .disclaimer {
            color: #94a3b8 !important;
            font-style: italic;
            margin-bottom: 0px;
        }
        /* Tighten up native Streamlit dataframes and hide toolbar noise */
        [data-testid="stDataFrame"] {
            background-color: #0b0e14 !important;
            border: 1px solid #1e232d !important;
            border-radius: 6px !important;
            padding: 4px !important;
        }
        [data-testid="stElementToolbar"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("<p class='disclaimer'>⚠️ Educational & Technical Analysis Only — Not financial advice.</p>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================================
# 2. RAW PLAYBOOK DATA ROUTINE (CLEANED & INVERSION FIXES)
# ====================================================================
def get_raw_playbook():
    return [
        # --- XPO SETUPS ---
        {"Ticker": "XPO", "Scenario": "Bullish Breakout Expansion", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$225.50 – $227.00", "Stop_Loss": "$214.00", "Targets": "$248.00"},
        {"Ticker": "XPO", "Scenario": "Pullback Support Long", "Direction": "Long", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$202.00 – $205.50", "Stop_Loss": "$190.00", "Targets": "$236.00"},
        {"Ticker": "XPO", "Scenario": "Failed Breakout (Mean Short)", "Direction": "Short", "Play Status": "⏳ Monitoring Setup", "Entry": "$228.50 – $230.50", "Stop_Loss": "$239.00", "Targets": "$205.00"},
        
        # --- TKO SETUPS ---
        {"Ticker": "TKO", "Scenario": "Bullish Breakout Expansion", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$210.00 – $212.00", "Stop_Loss": "$201.00", "Targets": "$228.00"},
        {"Ticker": "TKO", "Scenario": "Range Continuation Play", "Direction": "Short", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$202.00 – $204.00", "Stop_Loss": "$216.00", "Targets": "$193.00"},
        {"Ticker": "TKO", "Scenario": "Deeper Value Support Pullback", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$188.00 – $192.00", "Stop_Loss": "$180.00", "Targets": "$215.00"},
        
        # --- TE SETUPS ---
        {"Ticker": "TE", "Scenario": "Conservative Swing", "Direction": "Short", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$9.25 – $9.55", "Stop_Loss": "$10.15", "Targets": "$8.80"},
        {"Ticker": "TE", "Scenario": "Aggressive Breakout", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$10.40 – $10.65", "Stop_Loss": "$9.55", "Targets": "$12.00"},
        {"Ticker": "TE", "Scenario": "Deeper Value Dip", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$8.85 – $9.05", "Stop_Loss": "$8.00", "Targets": "$11.50"},
        
        # --- SES SETUPS ---
        {"Ticker": "SES", "Scenario": "ZLEMA Resistance Break", "Direction": "Short", "Play Status": "🎯 Running In Profit", "Entry": "$1.28 – $1.32", "Stop_Loss": "$1.41", "Targets": "$1.12"},
        {"Ticker": "SES", "Scenario": "Support Shelf Flush", "Direction": "Short", "Play Status": "⏳ Monitoring Setup", "Entry": "$0.98 – $1.02", "Stop_Loss": "$1.08", "Targets": "$0.88"},
        
        # --- GE SETUPS ---
        {"Ticker": "GE", "Scenario": "Pullback Long", "Direction": "Long", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$312.00 – $319.00", "Stop_Loss": "$295.00", "Targets": "$355.00"},
        {"Ticker": "GE", "Scenario": "Breakout Expansion", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$338.00 – $342.00", "Stop_Loss": "$320.00", "Targets": "$385.00"},
        {"Ticker": "GE", "Scenario": "Failed Breakout Short", "Direction": "Short", "Play Status": "❌ STOPPED OUT", "Entry": "$332.00 – $337.00", "Stop_Loss": "$355.00", "Targets": "$299.00"},
        
        # --- EOSE SETUPS ---
        {"Ticker": "EOSE", "Scenario": "Pullback Long Accumulation", "Direction": "Long", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$6.95", "Stop_Loss": "$6.40", "Targets": "$10.00"},
        {"Ticker": "EOSE", "Scenario": "Momentum Breakout", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$8.50", "Stop_Loss": "$7.70", "Targets": "$11.20"},
        {"Ticker": "EOSE", "Scenario": "Conservative Reversal Entry", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$7.40", "Stop_Loss": "$6.95", "Targets": "$8.80"}
    ]

# ====================================================================
# 3. PARSING & AUTOMATED MATHEMATICS ENGINE
# ====================================================================
def parse_price(val_str):
    nums = re.findall(r"\d+\.\d+|\d+", str(val_str))
    if not nums:
        return 0.0
    return sum(map(float, nums)) / len(nums)

def compute_matrix_metrics(df):
    rr_ratios = []
    pct_returns = []
    
    for _, row in df.iterrows():
        entry = parse_price(row['Entry'])
        stop = parse_price(row['Stop_Loss'])
        target = parse_price(row['Targets'])
        direction = row['Direction']
        
        if entry == 0.0 or stop == 0.0 or target == 0.0:
            rr_ratios.append("1:1.0")
            pct_returns.append("0.0%")
            continue
            
        if direction == "Long":
            risk = entry - stop
            reward = target - entry
        else:
            risk = stop - entry
            reward = entry - target
            
        risk = 0.01 if risk <= 0 else risk
        reward = 0.01 if reward <= 0 else reward
        
        return_pct = (reward / entry) * 100
        rr_ratios.append(f"1:{round(reward / risk, 1)}")
        pct_returns.append(f"+{round(return_pct, 1)}%")
        
    df['R:R Ratio'] = rr_ratios
    df['Est. Return'] = pct_returns
    return df

# ====================================================================
# 4. STREAMLIT RUNTIME EXECUTION
# ====================================================================
refresh_speed = st.sidebar.slider("Refresh Loop Interval (Seconds)", 5, 60, 15)
dashboard_container = st.empty()

while True:
    raw_data = get_raw_playbook()
    working_df = pd.DataFrame(raw_data)
    tickers_list = list(working_df['Ticker'].unique())
    
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
            
    working_df['Live Price'] = working_df['Ticker'].map(live_prices).round(2)
    working_df = compute_matrix_metrics(working_df)
    
    # 100% Dynamic TradingView routing layout mapping
    working_df['Chart Link'] = working_df['Ticker'].apply(lambda t: f"https://www.tradingview.com/symbols/{str(t).upper()}/")

    # ====================================================================
    # 5. DASHBOARD PRESENTATION LAYOUT
    # ====================================================================
    with dashboard_container.container():
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Active Setups", len(working_df))
        m2.metric("Unique Monitored Assets", working_df['Ticker'].nunique())
        m3.metric("Stream Status", "● RUNNING", f"{refresh_speed}s loop")
        
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        
        # Order columns for clean display
        ordered_cols = ['Ticker', 'Scenario', 'Play Status', 'Live Price', 'Entry', 'Stop_Loss', 'Targets', 'Est. Return', 'R:R Ratio', 'Chart Link']
        display_df = working_df[ordered_cols]
        
        # Native dataframe viewport with locked height bounding box
        st.dataframe(
            display_df,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Scenario": st.column_config.TextColumn("Scenario", width="medium"),
                "Play Status": st.column_config.TextColumn("Status", width="medium"),
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f", width="small"),
                "Entry": st.column_config.TextColumn("Entry Zone", width="medium"),
                "Stop_Loss": st.column_config.TextColumn("Stop Loss", width="small"),
                "Targets": st.column_config.TextColumn("Target", width="small"),
                "Est. Return": st.column_config.TextColumn("Est. Return", width="small"),
                "R:R Ratio": st.column_config.TextColumn("R:R", width="small"),
                "Chart Link": st.column_config.LinkColumn("Chart", display_text="TradingView ↗", width="small")
            },
            hide_index=True,
            use_container_width=True,
            height=380
        )
        
        st.caption(f"System Heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    time.sleep(refresh_speed)
