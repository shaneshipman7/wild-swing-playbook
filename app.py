import streamlit as st
import pandas as pd
import yfinance as yf
import time
from datetime import datetime

# ====================================================================
# 1. PAGE SETUP & NATIVE STYLE INJECTION
# ====================================================================
st.set_page_config(
    page_title="Wild Swing Trades • Live Playbook",
    page_icon="📈",
    layout="wide"
)

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
st.markdown("<p class='disclaimer'>⚠️ Educational & Technical Analysis Only — Not financial advice.</p>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================================
# 2. CLEAN PRIMARY MATRIX ARCHIVE WITH EXPLICIT STATES
# ====================================================================
def load_clean_scratch_data():
    scratch_playbook = [
        # --- XPO SETUPS ---
        {"Ticker": "XPO", "Scenario": "Bullish Breakout Expansion", "Play Status": "⏳ Monitoring Setup", "Entry": "$225.50 – $227.00", "Stop_Loss": "$236.00", "Targets": "$248.00", "Probability": "38%", "R_R": "1:1.8"},
        {"Ticker": "XPO", "Scenario": "Pullback Support Long", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$202.00 – $205.50", "Stop_Loss": "$224.00", "Targets": "$236.00", "Probability": "52%", "R_R": "1:2.4"},
        {"Ticker": "XPO", "Scenario": "Failed Breakout (Mean Short)", "Play Status": "⏳ Monitoring Setup", "Entry": "$228.50 – $230.50", "Stop_Loss": "$214.00", "Targets": "$205.00", "Probability": "25%", "R_R": "1:1.9"},
        
        # --- TKO SETUPS ---
        {"Ticker": "TKO", "Scenario": "Bullish Breakout Expansion", "Play Status": "⏳ Monitoring Setup", "Entry": "$210.00 – $212.00", "Stop_Loss": "$228.00", "Targets": "$199.50", "Probability": "45%", "R_R": "1:1.8"},
        {"Ticker": "TKO", "Scenario": "Range Continuation Play", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$202.00 – $204.00", "Stop_Loss": "$216.00", "Targets": "$193.00", "Probability": "55%", "R_R": "1:1.6"},
        {"Ticker": "TKO", "Scenario": "Deeper Value Support Pullback", "Play Status": "⏳ Monitoring Setup", "Entry": "$188.00 – $192.00", "Stop_Loss": "$215.00", "Targets": "$180.00", "Probability": "35%", "R_R": "1:2.3"},
        
        # --- TE SETUPS ---
        {"Ticker": "TE", "Scenario": "Conservative Swing", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$9.25 – $9.55", "Stop_Loss": "$11.50 / $12.50", "Targets": "$8.80", "Probability": "55%", "R_R": "1:2.1"},
        {"Ticker": "TE", "Scenario": "Aggressive Breakout", "Play Status": "⏳ Monitoring Setup", "Entry": "$10.40 – $10.65", "Stop_Loss": "$11.50 / $12.50", "Targets": "$9.55", "Probability": "48%", "R_R": "1:2.3"},
        {"Ticker": "TE", "Scenario": "Deeper Value Dip", "Play Status": "⏳ Monitoring Setup", "Entry": "$8.85 – $9.05", "Stop_Loss": "$11.50", "Targets": "$8.00", "Probability": "40%", "R_R": "1:2.8"},
        
        # --- SES SETUPS ---
        {"Ticker": "SES", "Scenario": "ZLEMA Resistance Break", "Play Status": "🎯 Running In Profit", "Entry": "$1.28 – $1.32", "Stop_Loss": "$1.65", "Targets": "$1.12", "Probability": "35%", "R_R": "2.1:1"},
        {"Ticker": "SES", "Scenario": "Support Shelf Flush", "Play Status": "⏳ Monitoring Setup", "Entry": "$0.98 – $1.02", "Stop_Loss": "$1.48", "Targets": "$0.88", "Probability": "28%", "R_R": "3.0:1"},
        
        # --- GE SETUPS ---
        {"Ticker": "GE", "Scenario": "Pullback Long", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$312.00 – $319.00", "Stop_Loss": "$338.00", "Targets": "$355.00", "Probability": "62%", "R_R": "+8.5% – 13.7%"},
        {"Ticker": "GE", "Scenario": "Breakout Expansion", "Play Status": "⏳ Monitoring Setup", "Entry": "$338.00 – $342.00", "Stop_Loss": "$365.00", "Targets": "$385.00", "Probability": "48%", "R_R": "+7.9% – 13.9%"},
        {"Ticker": "GE", "Scenario": "Failed Breakout Short", "Play Status": "❌ STOPPED OUT", "Entry": "$332.00 – $337.00", "Stop_Loss": "$313.00", "Targets": "$299.00", "Probability": "35%", "R_R": "-5.7% – 10.2%"},
        
        # --- EOSE SETUPS ---
        {"Ticker": "EOSE", "Scenario": "Pullback Long Accumulation", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$6.95", "Stop_Loss": "$10.00", "Targets": "$6.40", "Probability": "58%", "R_R": "5.6:1"},
        {"Ticker": "EOSE", "Scenario": "Momentum Breakout", "Play Status": "⏳ Monitoring Setup", "Entry": "$8.50", "Stop_Loss": "$11.20", "Targets": "$7.70", "Probability": "47%", "R_R": "3.4:1"},
        {"Ticker": "EOSE", "Scenario": "Conservative Reversal Entry", "Play Status": "⏳ Monitoring Setup", "Entry": "$7.40", "Stop_Loss": "$8.80", "Targets": "$6.95", "Probability": "65%", "R_R": "3.2:1"}
    ]
    return pd.DataFrame(scratch_playbook)

refresh_speed = st.sidebar.slider("Refresh Loop Interval (Seconds)", 5, 60, 15)
dashboard_container = st.empty()

# ====================================================================
# 3. LIVE MARKET RUNTIME LOOP
# ====================================================================
while True:
    working_df = load_clean_scratch_data()
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
            
    # Direct Map Variables
    working_df['Live Price'] = working_df['Ticker'].map(live_prices).round(2)
    working_df['Entry Zone'] = working_df['Entry']
    working_df['Stop Loss'] = working_df['Stop_Loss']
    working_df['Targets'] = working_df['Targets']
    working_df['Est. Probability'] = working_df['Probability']
    working_df['R:R Ratio'] = working_df['R_R']
    working_df['Chart Link'] = working_df['Ticker'].apply(lambda t: f"https://www.tradingview.com/symbols/{t}/")

    # ====================================================================
    # 4. DASHBOARD PRESENTATION LAYOUT
    # ====================================================================
    with dashboard_container.container():
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Active Setups", len(working_df))
        m2.metric("Unique Monitored Assets", working_df['Ticker'].nunique())
        m3.metric("Stream Status", "● RUNNING", f"{refresh_speed}s loop")
        
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        
        intended_columns = ['Ticker', 'Scenario', 'Play Status', 'Live Price', 'Entry Zone', 'Stop Loss', 'Targets', 'Est. Probability', 'R:R Ratio', 'Chart Link']
        display_output_df = working_df[intended_columns]
        
        st.dataframe(
            display_output_df,
            column_config={
                "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
                "Play Status": st.column_config.TextColumn("🚨 Status badge", width="medium"),
                "Chart Link": st.column_config.LinkColumn("Chart Link", display_text="TradingView ↗")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.caption(f"System Heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    time.sleep(refresh_speed)
