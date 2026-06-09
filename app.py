import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import requests

# Set up page configuration for mobile responsiveness
st.set_page_config(
    page_title="Wild Swing Trades Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Live Feed Parser: Reads exact values from your Blogger labels
@st.cache_data(ttl=60)
def fetch_live_blog_data():
    FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default"
    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
    playbooks = []
    
    try:
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
            
            if not blog_url or "template" in title.lower():
                continue

            # Default fallback values
            win_probability = 0.50
            avg_return = 0.0
            regime = "Trending"

            # Pull metrics directly from the post category/label elements
            for category in entry.findall('atom:category', namespaces):
                term = category.attrib.get('term', '')
                
                # Check for Prob tag (e.g., "Prob: 62")
                if "prob:" in term.lower():
                    try:
                        val = term.split(":")[-1].strip()
                        win_probability = float(val) / 100.0
                    except:
                        pass
                
                # Check for Return tag (e.g., "Ret: 4.5")
                elif "ret:" in term.lower():
                    try:
                        val = term.split(":")[-1].strip()
                        avg_return = float(val)
                    except:
                        pass
                
                # Check for Regime tag
                elif "regime:" in term.lower():
                    regime = term.split(":")[-1].strip()

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
    st.caption("100% Automated Performance Matrix")
    st.divider()

    if df.empty:
        st.warning("Connecting to wildswingtrades.blogspot.com...")
    else:
        # Sidebar Filters
        st.sidebar.header("Filter Strategy Metrics")
        min_prob = st.sidebar.slider("Minimum Win Probability", 0.0, 1.0, 0.10, 0.01, format="%.0f%%")
        min_ret = st.sidebar.slider("Minimum Avg Return (%)", -5.0, 50.0, -5.0, 0.5, format="%.1f%%")

        available_regimes = df['regime'].unique().tolist()
        selected_regimes = st.sidebar.multiselect("Market Regimes", options=available_regimes, default=available_regimes)

        # Filter Data
        filtered_df = df[
            (df['win_probability'] >= min_prob) & 
            (df['avg_return'] >= min_ret) &
            (df['regime'].isin(selected_regimes))
        ]

        # Highlight Cards
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Highest Win Prob in View", f"{filtered_df['win_probability'].max() * 100:.0f}%")
            with col2:
                st.metric("Best Avg Return in View", f"{filtered_df['avg_return'].max():.1f}%")
        
        st.write("### Playbook Data Matrix")
        st.caption("💡 Tap a column header to instantly sort by that metric.")

        # Render Dataframe
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
        
