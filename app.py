import streamlit as st
import pandas as pd

# Set up page configuration for mobile responsiveness
st.set_page_config(
    page_title="Wild Swing Trades Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" # Keeps it clean on mobile screens
)

# 1. Point to your raw GitHub CSV file
# Configured specifically for shaneshipman7/wild-swing-playbook
CSV_URL = "https://raw.githubusercontent.com/shaneshipman7/wild-swing-playbook/main/playbooks.csv"

@st.cache_data(ttl=600) # Caches the data for 10 minutes so it loads instantly
def load_data(url):
    # Read the data from GitHub
    data = pd.read_csv(url)
    
    # Data Cleaning: Ensure numerical columns are floats so sorting works flawlessly
    data['win_probability'] = pd.to_numeric(data['win_probability'], errors='coerce').fillna(0.0)
    data['avg_return'] = pd.to_numeric(data['avg_return'], errors='coerce').fillna(0.0)
    
    return data

# Main Application Logic
try:
    df = load_data(CSV_URL)

    st.title("📊 Wild Swing Trades")
    st.caption("Playbook Performance Metrics & Analytics")
    st.divider()

    # 2. Sidebar / Mobile Menu Filters
    st.sidebar.header("Filter Strategy Metrics")
    
    # Slider for Probability (0.0 to 1.0)
    min_prob = st.sidebar.slider(
        "Minimum Win Probability", 
        min_value=0.0, 
        max_value=1.0, 
        value=0.40, 
        step=0.01,
        format="%.0f%%"
    )

    # Slider for Average Return
    min_ret = st.sidebar.slider(
        "Minimum Avg Return (%)", 
        min_value=-5.0, 
        max_value=15.0, 
        value=0.0, 
        step=0.5,
        format="%.1f%%"
    )

    # Categorical Filter for Regimes
    available_regimes = df['regime'].unique().tolist()
    selected_regimes = st.sidebar.multiselect(
        "Market Regimes", 
        options=available_regimes, 
        default=available_regimes
    )

    # 3. Apply Filters Mathematically
    filtered_df = df[
        (df['win_probability'] >= min_prob) & 
        (df['avg_return'] >= min_ret) &
        (df['regime'].isin(selected_regimes))
    ]

    # 4. Interactive Metric Highlight Cards
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            highest_win = filtered_df['win_probability'].max() * 100
            st.metric("Highest Win Prob in View", f"{highest_win:.0f}%")
        with col2:
            best_return = filtered_df['avg_return'].max()
            st.metric("Best Avg Return in View", f"{best_return:.1f}%")
    
    st.write("### Playbook Data Matrix")
    st.caption("💡 Tap a column header to change the sort order (e.g., highest return or best win probability).")

    # 5. Display the Interactive Sortable Dataframe
    st.dataframe(
        filtered_df,
        column_config={
            "play_id": st.column_config.TextColumn("ID", width="small"),
            "name": st.column_config.TextColumn("Play Name", width="medium"),
            "regime": st.column_config.TextColumn("Market Regime", width="medium"),
            "win_probability": st.column_config.NumberColumn(
                "Win Prob", 
                format="%.0f%%", 
                help="Historical baseline win rate"
            ),
            "avg_return": st.column_config.NumberColumn(
                "Avg Return", 
                format="%.1f%%", 
                help="Average percentage return per trade"
            ),
            "blog_url": st.column_config.LinkColumn(
                "Full Setup", 
                display_text="Read Playbook ↗"
            )
        },
        use_container_width=True,
        hide_index=True
    )
    
    if filtered_df.empty:
        st.warning("No plays match your current filter settings. Try lowering your slider thresholds.")

except Exception as e:
    st.error("Unable to properly render the playbook matrix.")
    st.info("Make sure your 'playbooks.csv' file exists in your repository, has data rows, and matches the correct column header spelling.")
    with st.expander("Debug Error Details"):
        st.code(e)
        
