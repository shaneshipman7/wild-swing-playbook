import streamlit as st
import pandas as pd
import yfinance as yf
import re
from datetime import datetime
import feedparser
from bs4 import BeautifulSoup

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

st.set_page_config(page_title="Wild Swing Trades • Live Playbook (Blog Synced)", page_icon="📈", layout="wide")

st.markdown("""
    <style>
        .main, [data-testid="stAppViewContainer"] { background-color: #020617 !important; }
        h1, h2, h3, p, span, label, li, div { color: #ffffff !important; }
        div[data-testid="stMetric"] { background-color: #0f172a !important; padding: 12px !important; border-radius: 8px !important; border: 1px solid #1e293b !important; }
        div[data-testid="stMetricValue"] div, div[data-testid="stMetricValue"] span { color: #2dd4bf !important; font_weight: 800 !important; }
        .disclaimer { color: #94a3b8 !important; font-style: italic; margin-bottom: 0px; }
        [data-testid="stDataFrame"] { background-color: #0b0e14 !important; border: 1px solid #1e232d !important; border-radius: 6px !important; padding: 4px !important; }
        [data-testid="stElementToolbar"] { display: none !important; }
        .stButton button { background-color: #0ea5e9 !important; color: white !important; border: none !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Wild Swing Trades — Playbook Intelligence Hub")
st.markdown("<p class='disclaimer'>⚠️ Educational & Technical Analysis Only — Not financial advice. Data auto-synced from your blog at wildswingtrades.blogspot.com (RSS).</p>", unsafe_allow_html=True)
st.markdown("---")

LOOKBACK_DEFAULT = 30
MAX_SETUPS_DEFAULT = 50

def make_zone(price, spread=0.018):
    if not price or price <= 0:
        return "TBD"
    low = round(price * (1 - spread), 2)
    high = round(price * (1 + spread), 2)
    return f"${low:.2f} - ${high:.2f}"

def parse_price(val_str, which="first"):
    nums = re.findall(r"\d+\.\d+|\d+", str(val_str))
    if not nums:
        return 0.0
    if which == "first":
        return float(nums[0])
    elif which == "last":
        return float(nums[-1])
    else:
        return sum(map(float, nums)) / len(nums)

def compute_matrix_metrics(df):
    rr_ratios, pct_returns = [], []
    for _, row in df.iterrows():
        entry = parse_price(row['Entry'], "first")
        stop = parse_price(row['Stop_Loss'], "first")
        target = parse_price(row['Targets'], "last")
        direction = row['Direction']

        if entry == 0.0 or stop == 0.0 or target == 0.0:
            rr_ratios.append("1:1.0")
            pct_returns.append("0.0%")
            continue

        if direction == "Long":
            risk = max(0.01, entry - stop)
            reward = max(0.01, target - entry)
        else:
            risk = max(0.01, stop - entry)
            reward = max(0.01, entry - target)

        rr = round(reward / risk, 1)
        pct = round((reward / entry) * 100, 1)

        rr_ratios.append(f"1:{rr}")
        pct_returns.append(f"+{pct}%")

    df['R:R Ratio'] = rr_ratios
    df['Est. Return'] = pct_returns
    return df

@st.cache_data(ttl=1800, show_spinner="Syncing latest plays from your blog...")
def get_raw_playbook(lookback_days: int = LOOKBACK_DEFAULT, max_setups: int = MAX_SETUPS_DEFAULT):
    FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss&max-results=50"
    try:
        feed = feedparser.parse(FEED_URL)
        if not feed.entries: raise ValueError("Empty feed")
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
                if days_old > lookback_days: continue
                content_html = entry.get("description", "") or entry.get("summary", "")
                soup = BeautifulSoup(content_html, "lxml")
                full_text = soup.get_text(separator=" ", strip=True)
                text_lower = full_text.lower()
                ticker_match = re.search(r'\$([A-Z]{2,5})\b', title)
                if not ticker_match:
                    ticker_match = re.search(r'\b([A-Z]{2,5})\b(?=.*(?:stock|inc|holdings|group|etf|fund))', title, re.IGNORECASE)
                if not ticker_match: continue
                ticker = ticker_match.group(1).upper()
                if ticker in seen_tickers: continue
                seen_tickers.add(ticker)

                scenario_base = title.split(":")[0].strip() if ":" in title else title[:60]
                scenario_base = re.sub(r'\$?[A-Z]{2,5}\b|\s*\(.*?\)\s*', '', scenario_base)
                scenario_base = re.sub(r'\b(Inc|Corp|Corporation|Holdings|Group|Technologies|Systems|Company|Inc\.|Ltd\.?|LLC)\b', '', scenario_base, flags=re.IGNORECASE)
                scenario_base = re.sub(r'\s+', ' ', scenario_base).strip()
                if len(scenario_base) > 45:
                    scenario_base = scenario_base[:45].rsplit(' ', 1)[0]
                if not scenario_base:
                    scenario_base = "Play"

                direction = "Long"
                if any(kw in text_lower for kw in ["short", "bearish", "resistance play", "failed breakout short"]): direction = "Short"

                def find_price(keyword_regex, text, fallback=None):
                    pattern = rf'{keyword_regex}[^.]*?\$?(\d{{1,4}}(?:\.\d{{1,2}})?)'
                    m = re.search(pattern, text, re.IGNORECASE)
                    if m:
                        try:
                            val = float(m.group(1))
                            if 0.5 < val < 1000: return val
                        except: pass
                    return fallback

                current_price = find_price(r'(?:near|around|consolidat|trading at|close|currently)', full_text)
                support = find_price(r'support', full_text, current_price * 0.96 if current_price else None)
                resistance = find_price(r'(?:resistance|target|breakout to|upside to)', full_text)
                if not resistance and current_price:
                    all_prices = [float(p) for p in re.findall(r'\$?(\d{1,4}(?:\.\d{1,2})?)', full_text)]
                    higher = [p for p in all_prices if p > (current_price or 0) * 1.05]
                    if higher: resistance = max(higher[:5])

                base_status = "⏳ Monitoring Setup"
                if any(kw in text_lower for kw in ["break out", "breaks out", "surge", "explosive", "reclaim", "new high"]): base_status = "🟢 Momentum / Breakout Setup"
                elif any(kw in text_lower for kw in ["pullback", "dip buy", "value support", "consolidat"]): base_status = "🟢 IN ENTRY ZONE"
                if days_old <= 1: base_status = "🆕 Fresh • " + base_status

                plays_for_this = []
                if support or current_price:
                    entry_p = support or (current_price * 0.97 if current_price else 0)
                    stop_p = support * 0.93 if support and support > 0 else (entry_p * 0.90 if entry_p > 0 else 0)
                    tgt_p = resistance or (current_price * 1.12 if current_price else entry_p * 1.15)
                    if direction == "Long" and tgt_p and entry_p and tgt_p < entry_p: tgt_p = entry_p * 1.18
                    plays_for_this.append({
                        "Ticker": ticker,
                        "Scenario": f"{scenario_base} — Pullback/Support Play",
                        "Direction": direction,
                        "Play Status": base_status,
                        "Entry": make_zone(entry_p),
                        "Stop_Loss": f"${stop_p:.2f}" if stop_p > 0 else "TBD",
                        "Targets": make_zone(tgt_p),
                        "Blog Link": link,
                        "Pub Date": pub_date.strftime("%Y-%m-%d"),
                        "Days Old": days_old
                    })

                if current_price or resistance:
                    entry_p2 = resistance or (current_price * 1.03 if current_price else 0)
                    stop_p2 = (current_price * 0.97 if current_price else entry_p2 * 0.95) if direction == "Long" else (entry_p2 * 1.04)
                    tgt_p2 = (resistance * 1.15 if resistance else (current_price * 1.22 if current_price else 0)) if direction == "Long" else (current_price * 0.88 if current_price else 0)
                    if direction == "Long" and tgt_p2 and entry_p2 and tgt_p2 < entry_p2 * 1.08: tgt_p2 = entry_p2 * 1.20
                    plays_for_this.append({
                        "Ticker": ticker,
                        "Scenario": f"{scenario_base} — Breakout/Expansion Play",
                        "Direction": direction,
                        "Play Status": base_status.replace("IN ENTRY ZONE", "⏳ Monitoring Breakout"),
                        "Entry": make_zone(entry_p2),
                        "Stop_Loss": f"${stop_p2:.2f}" if stop_p2 > 0 else "TBD",
                        "Targets": make_zone(tgt_p2),
                        "Blog Link": link,
                        "Pub Date": pub_date.strftime("%Y-%m-%d"),
                        "Days Old": days_old
                    })

                for p in plays_for_this[:2]:
                    all_plays.append(p)
                if len(all_plays) >= max_setups: break
            except Exception: continue

        if not all_plays: return get_fallback_playbook()
        all_plays.sort(key=lambda x: (x.get("Days Old", 99), x["Ticker"]))
        return all_plays
    except Exception as e:
        st.warning(f"Blog sync issue: {str(e)[:150]}. Showing fallback data.")
        return get_fallback_playbook()

def get_fallback_playbook():
    return [
        {"Ticker": "XPO", "Scenario": "Bullish Breakout Expansion", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$225.50 - $227.00", "Stop_Loss": "$214.00", "Targets": "$248.00", "Blog Link": "", "Pub Date": "2026-06-05", "Days Old": 1},
        {"Ticker": "XPO", "Scenario": "Pullback Support Long", "Direction": "Long", "Play Status": "🟢 IN ENTRY ZONE", "Entry": "$202.00 - $205.50", "Stop_Loss": "$190.00", "Targets": "$236.00", "Blog Link": "", "Pub Date": "2026-06-05", "Days Old": 1},
        {"Ticker": "TKO", "Scenario": "Bullish Breakout Expansion", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$210.00 - $212.00", "Stop_Loss": "$201.00", "Targets": "$228.00", "Blog Link": "", "Pub Date": "2026-06-05", "Days Old": 1},
        {"Ticker": "TE", "Scenario": "Aggressive Breakout", "Direction": "Long", "Play Status": "⏳ Monitoring Setup", "Entry": "$10.40 - $10.65", "Stop_Loss": "$9.55", "Targets": "$12.00", "Blog Link": "", "Pub Date": "2026-06-05", "Days Old": 1},
        {"Ticker": "UMAC", "Scenario": "Breakout Expansion (from blog)", "Direction": "Long", "Play Status": "🟢 Momentum / Breakout Setup", "Entry": "$26.00 - $27.50", "Stop_Loss": "$24.00", "Targets": "$42.00", "Blog Link": "https://wildswingtrades.blogspot.com/2026/06/unusual-machines-umac-surges-as.html", "Pub Date": "2026-06-05", "Days Old": 1}
    ]

def enrich_with_live_prices(df):
    tickers = df['Ticker'].unique().tolist()
    live_prices = {}
    if tickers:
        try:
            data = yf.download(" ".join(tickers), period="1d", interval="1m", group_by='ticker', progress=False, auto_adjust=True)
            for t in tickers:
                try:
                    live_prices[t] = round(float(data[t]['Close'].iloc[-1] if len(tickers) > 1 else data['Close'].iloc[-1]), 2)
                except:
                    live_prices[t] = None
        except:
            pass
    df['Live Price'] = df['Ticker'].map(live_prices)
    return df

# Initial load
raw_plays = get_raw_playbook(LOOKBACK_DEFAULT, MAX_SETUPS_DEFAULT)
working_df = pd.DataFrame(raw_plays)
for col in ['Ticker', 'Scenario', 'Direction', 'Play Status', 'Entry', 'Stop_Loss', 'Targets', 'Blog Link', 'Pub Date', 'Days Old']:
    if col not in working_df.columns: working_df[col] = ""
working_df = enrich_with_live_prices(working_df)
working_df = compute_matrix_metrics(working_df)

if HAS_AUTOREFRESH:
    st_autorefresh(interval=25 * 1000, limit=200, key="price_autorefresh")

with st.sidebar:
    st.header("Controls")
    lookback_days = st.slider("Look back (days) from blog", 7, 90, LOOKBACK_DEFAULT, 1)
    max_setups = st.slider("Max setups to display", 10, 100, MAX_SETUPS_DEFAULT, 5)

    st.subheader("Filters")
    status_options = sorted(working_df['Play Status'].dropna().unique().tolist())
    selected_statuses = st.multiselect("Play Status", options=status_options, default=status_options)
    ticker_filter = st.text_input("Ticker contains", "")

    if st.button("🔄 Force Full Refresh (Blog + Prices)", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.button("📈 Refresh Live Prices Only", use_container_width=True):
        st.rerun()
    st.divider()
    st.caption("Blog data refreshes every \~30 min. Live prices \~every 25s.")

if lookback_days != LOOKBACK_DEFAULT:
    raw_plays = get_raw_playbook(lookback_days, max_setups)
    working_df = pd.DataFrame(raw_plays)
    for col in ['Ticker', 'Scenario', 'Direction', 'Play Status', 'Entry', 'Stop_Loss', 'Targets', 'Blog Link', 'Pub Date', 'Days Old']:
        if col not in working_df.columns: working_df[col] = ""
    working_df = enrich_with_live_prices(working_df)
    working_df = compute_matrix_metrics(working_df)

filtered_df = working_df.copy()
if selected_statuses:
    filtered_df = filtered_df[filtered_df['Play Status'].isin(selected_statuses)]
if ticker_filter:
    filtered_df = filtered_df[filtered_df['Ticker'].str.contains(ticker_filter.upper(), case=False, na=False)]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Active Setups", len(working_df))
m2.metric("Showing after filters", len(filtered_df))
m3.metric("Data Window", f"Last {lookback_days} days from blog")
m4.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))

st.markdown("### 📋 Active Playbook — Live from Your Wild Swing Trades Blog")
st.caption("Click any **Ticker** to open its TradingView chart directly. Best viewed in landscape on mobile.")

filtered_df['TickerLink'] = filtered_df['Ticker'].apply(lambda t: f"https://www.tradingview.com/symbols/{str(t).upper()}/")

ordered_cols = ['TickerLink', 'Play Status', 'Live Price', 'Entry', 'Stop_Loss', 'Targets', 'Est. Return', 'R:R Ratio', 'Pub Date', 'Blog Link', 'Scenario']
display_df = filtered_df[[c for c in ordered_cols if c in filtered_df.columns]]

st.dataframe(display_df, column_config={
    "TickerLink": st.column_config.LinkColumn("Ticker", display_text=r"/symbols/([^/]+)", width="small"),
    "Scenario": st.column_config.TextColumn("Scenario", width="large"),
    "Play Status": st.column_config.TextColumn("Status", width="medium"),
    "Live Price": st.column_config.NumberColumn("Live Price", format="$%.2f", width="small"),
    "Entry": st.column_config.TextColumn("Entry Zone", width="medium"),
    "Stop_Loss": st.column_config.TextColumn("Stop Loss", width="small"),
    "Targets": st.column_config.TextColumn("Target Zone", width="medium"),
    "Est. Return": st.column_config.TextColumn("Est Ret", width="small"),
    "R:R Ratio": st.column_config.TextColumn("R:R", width="small"),
    "Pub Date": st.column_config.TextColumn("Blog Date", width="small"),
    "Blog Link": st.column_config.LinkColumn("Blog Post", display_text="Read Analysis ↗", width="medium")
}, hide_index=True, use_container_width=True, height=420)

with st.expander("💡 Filter tips"):
    st.markdown("""
    - Click the **Ticker** name to jump straight to the TradingView chart.
    - Use the two sliders to control how many plays and how far back.
    - On mobile, rotate to landscape for the full table.
    """)

st.caption(f"Source: wildswingtrades.blogspot.com RSS • v3.9 (honest R:R) • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CDT")
