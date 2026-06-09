import streamlit as st
import pandas as pd
import yfinance as yf
import re
import glob
from datetime import datetime
from pathlib import Path
import feedparser
from bs4 import BeautifulSoup

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ==================== PAGE SETUP ====================
st.set_page_config(page_title="Wild Swing Trades • Live Playbook", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        .main, [data-testid="stAppViewContainer"] { background-color: #020617 !important; }
        h1, h2, h3, p, span, label, li, div { color: #ffffff !important; }
        div[data-testid="stMetric"] { background-color: #0f172a !important; padding: 12px !important; border-radius: 8px !important; border: 1px solid #1e293b !important; }
        div[data-testid="stMetricValue"] div, div[data-testid="stMetricValue"] span { color: #2dd4bf !important; font-weight: 800 !important; }
        .disclaimer { color: #94a3b8 !important; font-style: italic; margin-bottom: 0px; }
        [data-testid="stDataFrame"] { background-color: #0b0e14 !important; border: 1px solid #1e232d !important; border-radius: 6px !important; padding: 4px !important; }
        [data-testid="stElementToolbar"] { display: none !important; }
        .stButton button { background-color: #0ea5e9 !important; color: white !important; border: none !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("<p class='disclaimer'>⚠️ Educational & Technical Analysis Only — Not financial advice. Data from daily CSV + live prices.</p>", unsafe_allow_html=True)
st.markdown("---")

# ==================== DATA LOADING ====================
def find_latest_csv():
    """Find the most recent Master_Playbook_Database_*.csv in the repo root."""
    files = glob.glob("Master_Playbook_Database_*.csv")
    if not files:
        return None
    # Sort by filename date (newest first)
    files.sort(reverse=True)
    return files[0]

def load_playbook_from_csv(csv_path):
    try:
        df = pd.read_csv(csv_path)
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
        
        # Standardize important columns
        column_map = {
            'Stop_Loss': 'Stop_Loss',
            'Targets': 'Targets',
            'R_R_Ratio': 'R:R Ratio',
            'Est_Probability': 'Prob',
            'Link': 'Blog Link',
            'Current_Price': 'Live Price'
        }
        
        # Rename if they exist
        for old, new in column_map.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        # Add missing columns with defaults
        for col in ['Entry', 'Stop_Loss', 'Targets', 'R:R Ratio', 'Prob', 'Blog Link', 'Scenario']:
            if col not in df.columns:
                df[col] = ""
        
        df['Source'] = 'CSV'
        return df
    except Exception as e:
        st.warning(f"Could not load CSV: {e}")
        return None

def get_raw_playbook_fallback(lookback_days=30):
    # Original blog scraping logic (kept as fallback)
    FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss&max-results=50"
    try:
        feed = feedparser.parse(FEED_URL)
        all_plays = []
        seen_tickers = set()
        now = datetime.now()
        
        for entry in feed.entries:
            try:
                title = entry.get("title", "")
                link = entry.get("link", "")
                pub_parsed = entry.get("published_parsed")
                pub_date = datetime(*pub_parsed[:6]) if pub_parsed else now
                days_old = (now - pub_date).days
                if days_old > lookback_days: 
                    continue
                
                content_html = entry.get("description", "") or entry.get("summary", "")
                soup = BeautifulSoup(content_html, "lxml")
                full_text = soup.get_text(separator=" ", strip=True)
                text_lower = full_text.lower()
                
                ticker_match = re.search(r'\$([A-Z]{2,5})\b', title)
                if not ticker_match:
                    ticker_match = re.search(r'\b([A-Z]{2,5})\b(?=.*(?:stock|inc|holdings|group|etf|fund))', title, re.IGNORECASE)
                if not ticker_match: 
                    continue
                ticker = ticker_match.group(1).upper()
                if ticker in seen_tickers: 
                    continue
                seen_tickers.add(ticker)

                scenario_base = title.split(":")[0].strip() if ":" in title else title[:60]
                scenario_base = re.sub(r'\$?[A-Z]{2,5}\b|\s*\(.*?\)\s*', '', scenario_base)
                scenario_base = re.sub(r'\b(Inc|Corp|Corporation|Holdings|Group|Technologies|Systems|Company|Inc\.|Ltd\.?|LLC)\b', '', scenario_base, flags=re.IGNORECASE)
                scenario_base = re.sub(r'\s+', ' ', scenario_base).strip()
                if len(scenario_base) > 45:
                    scenario_base = scenario_base[:45].rsplit(' ', 1)[0] or "Play"

                direction = "Long"
                if any(kw in text_lower for kw in ["short", "bearish", "resistance play", "failed breakout short"]): 
                    direction = "Short"

                def find_price(keyword_regex, text, fallback=None):
                    pattern = rf'{keyword_regex}[^.]*?\$?(\d{{1,4}}(?:\.\d{{1,2}})?)'
                    m = re.search(pattern, text, re.IGNORECASE)
                    if m:
                        try:
                            val = float(m.group(1))
                            if 0.5 < val < 1000: 
                                return val
                        except: 
                            pass
                    return fallback

                current_price = find_price(r'(?:near|around|consolidat|trading at|close|currently)', full_text)
                support = find_price(r'support', full_text, current_price * 0.96 if current_price else None)
                resistance = find_price(r'(?:resistance|target|breakout to|upside to)', full_text)
                
                if not resistance and current_price:
                    all_prices = [float(p) for p in re.findall(r'\$?(\d{1,4}}(?:\.\d{{1,2}})?)', full_text)]
                    higher = [p for p in all_prices if p > (current_price or 0) * 1.05]
                    if higher: 
                        resistance = max(higher[:5])

                base_status = "⏳ Monitoring Setup"
                if any(kw in text_lower for kw in ["break out", "breaks out", "surge", "explosive", "reclaim", "new high"]): 
                    base_status = "🟢 Momentum / Breakout Setup"
                elif any(kw in text_lower for kw in ["pullback", "dip buy", "value support", "consolidat"]): 
                    base_status = "🟢 IN ENTRY ZONE"
                if days_old <= 1: 
                    base_status = "🆕 Fresh • " + base_status

                def make_zone(price, spread=0.018):
                    if not price or price <= 0: 
                        return "TBD"
                    low = round(price * (1 - spread), 2)
                    high = round(price * (1 + spread), 2)
                    return f"${low:.2f} – \( {high:.2f}" if low != high else f" \){low:.2f}"

                plays_for_this = []
                if support or current_price:
                    entry_p = support or (current_price * 0.97 if current_price else 0)
                    stop_p = support * 0.93 if support and support > 0 else (entry_p * 0.90 if entry_p > 0 else 0)
                    tgt_p = resistance or (current_price * 1.12 if current_price else entry_p * 1.15)
                    if direction == "Long" and tgt_p and entry_p and tgt_p < entry_p: 
                        tgt_p = entry_p * 1.18
                    plays_for_this.append({
                        "Ticker": ticker, "Scenario": f"{scenario_base} — Pullback/Support Play", 
                        "Direction": direction, "Play Status": base_status, 
                        "Entry": make_zone(entry_p), "Stop_Loss": f"${stop_p:.2f}" if stop_p > 0 else "TBD", 
                        "Targets": make_zone(tgt_p), "Prob": "N/A", "Blog Link": link,
                        "Pub Date": pub_date.strftime("%Y-%m-%d"), "Days Old": days_old, "Source": "Blog"
                    })
                
                all_plays.extend(plays_for_this)
            except:
                continue
                
        return pd.DataFrame(all_plays) if all_plays else pd.DataFrame()
    except:
        return pd.DataFrame()

def parse_price(val_str):
    if pd.isna(val_str):
        return 0.0
    nums = re.findall(r"\d+\.\d+|\d+", str(val_str))
    if not nums: 
        return 0.0
    return sum(map(float, nums)) / len(nums)

def compute_metrics(df):
    rr_list, pct_list = [], []
    for _, row in df.iterrows():
        entry = parse_price(row.get('Entry', 0))
        stop = parse_price(row.get('Stop_Loss', 0))
        target = parse_price(row.get('Targets', 0))
        live = row.get('Live Price', None)
        base = live if (live and live > 0.5) else entry

        # Use CSV R:R if it exists and looks valid
        csv_rr = str(row.get('R:R Ratio', ''))
        if csv_rr and ':' in csv_rr and 'N/A' not in csv_rr:
            rr_list.append(csv_rr)
        else:
            if entry == 0 or stop == 0 or target == 0:
                rr_list.append("N/A")
            else:
                risk = max(0.01, entry - stop)
                reward = max(0.01, target - base)
                rr = round(reward / risk, 1)
                if rr > 12: rr = 12
                rr_list.append(f"1:{rr}")

        # Est. Return from Live Price
        if base > 0 and target > 0:
            pct = round(((target - base) / base) * 100, 1)
            pct_list.append(f"+{pct}%" if pct > 0 else f"{pct}%")
        else:
            pct_list.append("N/A")

    df['R:R Ratio'] = rr_list
    df['Est. Return'] = pct_list
    return df

def enrich_live_prices(df):
    tickers = df['Ticker'].dropna().unique().tolist()
    if not tickers:
        return df
    try:
        data = yf.download(" ".join(tickers), period="5d", group_by='ticker', progress=False, auto_adjust=True)
        live = {}
        for t in tickers:
            try:
                if len(tickers) > 1:
                    live[t] = round(float(data[t]['Close'].iloc[-1]), 2)
                else:
                    live[t] = round(float(data['Close'].iloc[-1]), 2)
            except:
                live[t] = None
        df['Live Price'] = df['Ticker'].map(live)
    except:
        df['Live Price'] = None
    return df

# ==================== MAIN DATA LOAD ====================
csv_file = find_latest_csv()
if csv_file:
    working_df = load_playbook_from_csv(csv_file)
    if working_df is None or working_df.empty:
        working_df = get_raw_playbook_fallback()
else:
    working_df = get_raw_playbook_fallback()

if working_df.empty:
    st.error("No data available.")
    st.stop()

working_df = enrich_live_prices(working_df)
working_df = compute_metrics(working_df)

# ==================== UI ====================
if HAS_AUTOREFRESH:
    st_autorefresh(interval=30000, limit=200, key="refresh")

with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Force Refresh (Prices + Data)", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Setups", len(working_df))
col2.metric("Data Source", "CSV" if csv_file else "Blog (fallback)")
col3.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))

st.markdown("### 📋 Active Playbook — Live from Your Wild Swing Trades Blog")

# Display
display_cols = ['Ticker', 'Scenario', 'Play Status', 'Live Price', 'Entry', 'Stop_Loss', 'Targets', 'Est. Return', 'R:R Ratio', 'Prob', 'Blog Link']
for c in display_cols:
    if c not in working_df.columns:
        working_df[c] = ""

display_df = working_df[[c for c in display_cols if c in working_df.columns]].copy()

st.dataframe(
    display_df,
    column_config={
        "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f"),
        "Est. Return": st.column_config.TextColumn("Est. Return"),
        "R:R Ratio": st.column_config.TextColumn("R:R"),
        "Blog Link": st.column_config.LinkColumn("Blog Post", display_text="Read ↗"),
    },
    hide_index=True,
    use_container_width=True,
    height=450
)

st.caption(f"Source: {csv_file or 'Blog RSS fallback'} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CDT")
