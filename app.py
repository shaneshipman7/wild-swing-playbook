import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import requests
import re

# Set up page configuration for mobile responsiveness
st.set_page_config(
    page_title="Wild Swing Trades Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 1. Live Feed Parser: Pulls directly from the web in real-time
@st.cache_data(ttl=60) # Automatically checks your blog for updates every 60 seconds
def fetch_live_blog_data():
    # URL to your public live Blogger RSS/Atom feed
    FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default"
    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
    playbooks = []
    
    try:
        # Fetch the feed directly over the internet
        response = requests.get(FEED_URL, timeout=10)
        if response.status_code != 200:
            return pd.DataFrame(columns=["play_id", "name", "regime", "win_probability", "avg_return", "blog_url"])
            
        root = ET.fromstring(response.content)
        
        for entry in root.findall('atom:entry', namespaces):
            title = entry.find('atom:title', namespaces).text
            
            # Find the direct blog link
            blog_url = ""
            for link in entry.findall('atom:link', namespaces):
                if link.attrib.get('rel') == 'alternate':
                    blog_url = link.attrib.get('href')
                    break
            
            # Get the text content of the post
            content_element = entry.find('atom:content', namespaces)
            content_text = content_element.text if content_element is not None else ""
            
            if not content_text or not blog_url or "template" in title.lower():
                continue
                
            # --- Text Search Patterns for Metrics ---
            win_match = re.search(r'(?:win\s*rate|probability|win\s*prob).*?(\d+(?:\.\d+)?)\s*%', content_text, re.IGNORECASE)
            win_probability = float(win_match.group(1)) / 100.0 if win_match else 0.50
                
            return_match = re.search(r'(?:return|avg\s*return|profit).*?([+-]?\d+(?:\.\d+)?)\s*%', content_text, re.IGNORECASE)
            avg_return = float(return_match.group(1)) if return_match else 0.0
                
            # Detect Regime based on keywords
            regime = "Trending"
            if "mean reversion" in content_text.lower() or "fade" in content_text.lower():
                regime = "Mean Reverting"
            elif "high vol" in content_text.lower() or "breakout" in content_text.lower():
                regime = "High Volatility"

            play_id = f"WS-{len(playbooks) + 1:03d}"
            
            playbooks.append({
                "play_id": play_id,
                "name": title,
                "regime": regime,
                "win_probability": win_probability,
                "avg_return": avg_return,
                "blog_url": blog_url
            })
            
        return pd.DataFrame(playbooks)
    except Exception as e:
        return pd.DataFrame(columns=["play_id", "name", "regime", "win_probability", "avg_return", "blog_url"])

# Main Application Logic
try:
    df = fetch_live_blog_data()

    st.title("📊 Wild Swing Trades")
    st.caption("100% Automated Performance Matrix (Live Live Live)")
    st.divider()

    if df.empty:
        st.warning("Connecting to wildswingtrades.blogspot.com... If this stays blank, your dashboard cannot reach the blog URL.")
    else:
        # 2. Sidebar Filters
        st.sidebar.header("Filter Strategy Metrics")
        min_prob = st.sidebar.slider("Minimum Win Probability", 0.0, 1.0, 0.40, 0.01, format="%.0f%%")
        min_ret = st.sidebar.slider("Minimum Avg Return (%)", -5.0, 15.0, 0.0, 0.5, format="%.1f%%")

        available_regimes = df['regime'].unique().tolist()
        selected_regimes = st.sidebar.multiselect("Market Regimes", options=available_regimes, default=available_regimes)

        # 3. Filter Data
        filtered_df = df[
            (df['win_probability'] >= min_prob) & 
            (df['avg_return'] >= min_ret) &
            (df['regime'].isin(selected_regimes))
        ]

        # 4. Highlight Cards
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Highest Win Prob in View", f"{filtered_df['win_probability'].max() * 100:.0f}%")
            with col2:
                st.metric("Best Avg Return in View", f"{filtered_df['avg_return'].max():.1f}%")
        
        st.write("### Playbook Data Matrix")
        st.caption("💡 Tap a column header to instantly sort by that metric.")

        # 5. Render Sortable Dataframe
        st.dataframe(
            filtered_df,
            column_config={
                "play_id": st.column_config.TextColumn("ID", width="small"),
                "name": st.column_config.TextColumn("Play Name", width="large"),
                "regime": st.column_config.TextColumn("Market Regime", width="medium"),
                "win_probability": st.column_config.NumberColumn("Win Prob", format="%.0f%%", width="small"),
                "avg_return": st.column_config.NumberColumn("Avg Return", format="%.1f%%", width="small"),
                "blog_url": st.column_config.LinkColumn("Full Setup", display_text="Read ↗", width="small")
            },
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error("Dashboard error encountered.")
    with st.expander("Debug Details"):
        st.code(e)
        
