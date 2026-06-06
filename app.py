import streamlit as st
import pandas as pd
import yfinance as yf
import time
import re
from datetime import datetime
import streamlit.components.v1 as components

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
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("<p class='disclaimer'>⚠️ Educational & Technical Analysis Only — Not financial advice.</p>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================================
# 2. RAW PLAYBOOK DATA ROUTINE (CLEANED & INVERSION FIXES)
# ====================================================================
def get_raw_playbook():
    """
    Returns the clean setup blueprints. Stops and Targets have been inverted 
    where necessary to align with the correct trade directions.
    """
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
    """Extracts numeric float values from currency strings."""
    nums = re.findall(r"\d+\.\d+|\d+", str(val_str))
    if not nums:
        return 0.0
    return sum(map(float, nums)) / len(nums)

def compute_matrix_metrics(df):
    """Calculates true risk-reward ratios and target percentage returns dynamically."""
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
            return_pct = (reward / entry) * 100
        else: # Short play mechanics
            risk = stop - entry
            reward = entry - target
            return_pct = (reward / entry) * 100
            
        # Protection against division by zero anomalies
        risk = 0.01 if risk <= 0 else risk
        reward = 0.01 if reward <= 0 else reward
        
        ratio_multiplier = round(reward / risk, 1)
        rr_ratios.append(f"1:{ratio_multiplier}")
        pct_returns.append(f"+{round(return_pct, 1)}%")
        
    df['R:R Ratio'] = rr_ratios
    df['Return %'] = pct_returns
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
    
    # Live Pricing via Yahoo Finance Pipeline
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
    
    # Generate Webull exchange routes automatically based on ticker profiles
    def webull_url(ticker):
        exchange = "nyse" if ticker in ["GE", "TKO", "TE", "SES"] else "nasdaq"
        return f"https://www.webull.com/quote/{exchange}-{ticker.lower()}"

    # ====================================================================
    # 5. HIGH-DENSITY HTML MATRIX CODE GENERATION
    # ====================================================================
    table_rows = ""
    for _, row in working_df.iterrows():
        live_p_str = f"${row['Live Price']:.2f}" if pd.notnull(row['Live Price']) else "Loading..."
        status_color = "#02c076" if "ENTRY" in row['Play Status'] or "PROFIT" in row['Play Status'] else "#f6465d"
        status_bg = "rgba(2,192,118,0.1)" if "ENTRY" in row['Play Status'] or "PROFIT" in row['Play Status'] else "rgba(246,70,93,0.1)"
        if "Monitoring" in row['Play Status']:
            status_color, status_bg = "#848e9c", "rgba(132,142,156,0.1)"
            
        table_rows += f"""
        <tr style="border-bottom: 1px solid #1e232d; transition: background-color 0.15s;" onmouseover="this.style.backgroundColor='#161a25'" onmouseout="this.style.backgroundColor='transparent'">
            <td style="padding: 6px 8px; font-weight: bold; color: #ffffff;">{row['Ticker']}</td>
            <td style="padding: 6px 8px; color: #eaecef;">{row['Scenario']}</td>
            <td style="padding: 6px 8px;"><span style="color: {status_color}; background: {status_bg}; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 500; white-space: nowrap;">{row['Play Status']}</span></td>
            <td style="padding: 6px 8px; text-align: right; font-family: monospace; color: #ffffff;">{live_p_str}</td>
            <td style="padding: 6px 8px; color: #f0b90b; font-family: monospace; white-space: nowrap;">{row['Entry']}</td>
            <td style="padding: 6px 8px; text-align: right; color: #f6465d; font-family: monospace;">{row['Stop_Loss']}</td>
            <td style="padding: 6px 8px; text-align: right; color: #02c076; font-family: monospace;">{row['Targets']}</td>
            <td style="padding: 6px 8px; text-align: right; color: #02c076; font-weight: bold; font-family: monospace;">{row['Return %']}</td>
            <td style="padding: 6px 8px; text-align: center; font-family: monospace; color: #ffffff;">{row['R:R Ratio']}</td>
            <td style="padding: 6px 8px; text-align: center;"><a href="{webull_url(row['Ticker'])}" target="_blank" style="color: #4b89ff; text-decoration: none; font-size: 12px; font-weight: 500;">Webull ↗</a></td>
        </tr>
        """

    html_matrix_component = f"""
    <div style="background-color: #0b0e14; padding: 12px; border-radius: 8px; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="max-height: 420px; overflow-y: auto; overflow-x: auto; border: 1px solid #1e232d; border-radius: 4px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                <thead>
                    <tr style="border-bottom: 2px solid #232936; color: #848e9c; background-color: #12161f; position: sticky; top: 0; z-index: 10;">
                        <th style="padding: 8px; color: #848e9c;">Ticker</th>
                        <th style="padding: 8px; color: #848e9c;">Scenario</th>
                        <th style="padding: 8px; color: #848e9c;">Status</th>
                        <th style="padding: 8px; text-align: right; color: #848e9c;">Live Price</th>
                        <th style="padding: 8px; color: #848e9c;">Entry Zone</th>
                        <th style="padding: 8px; text-align: right; color: #f6465d;">Stop Loss</th>
                        <th style="padding: 8px; text-align: right; color: #02c076;">Target</th>
                        <th style="padding: 8px; text-align: right; color: #02c076;">Est. Return</th>
                        <th style="padding: 8px; text-align: center; color: #848e9c;">R:R</th>
                        <th style="padding: 8px; text-align: center; color: #848e9c;">Chart</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    """

    # Render dashboard blocks
    with dashboard_container.container():
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Active Setups", len(working_df))
        m2.metric("Unique Monitored Assets", working_df['Ticker'].nunique())
        m3.metric("Stream Status", "● RUNNING", f"{refresh_speed}s loop")
        
        st.markdown("### 📋 Active Playbook Run-Time Matrix")
        components.html(html_matrix_component, height=440, scrolling=False)
        st.caption(f"System Heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CST")
        
    time.sleep(refresh_speed)
