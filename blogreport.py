import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
import time
import glob
import os

# ================== CONFIG ==================
DAYS_BACK = 7
BLOG_RSS = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss"
# ============================================

def is_us_market_open():
    """Simple check if NYSE/NASDAQ is open (Mon-Fri 9:30 AM - 4:00 PM ET)."""
    ny_time = datetime.now(ZoneInfo("America/New_York"))
    if ny_time.weekday() >= 5:  # Sat or Sun
        return False
    if ny_time.hour < 9 or (ny_time.hour == 9 and ny_time.minute < 30):
        return False
    if ny_time.hour >= 16:
        return False
    return True

def load_last_known_prices():
    """Load last known prices from the most recent Master_Playbook CSV file."""
    csv_files = sorted(glob.glob("Master_Playbook_Database_*.csv"), reverse=True)
    if not csv_files:
        print("   No previous database found.")
        return {}
    
    latest_file = csv_files[0]
    try:
        df_old = pd.read_csv(latest_file)
        if 'Ticker' in df_old.columns and 'Current_Price' in df_old.columns:
            price_map = df_old.groupby('Ticker')['Current_Price'].last().to_dict()
            print(f"   ✅ Loaded last known prices from {os.path.basename(latest_file)}")
            return price_map
    except Exception as e:
        print(f"   Warning: Could not load previous prices: {e}")
    return {}

def get_latest_playbook_plays():
    print("Fetching latest posts from blog...")
    feed = feedparser.parse(BLOG_RSS)
    print(f"   Found {len(feed.entries)} total posts in feed")
    
    cutoff = datetime.now() - timedelta(days=DAYS_BACK)
    trade_rows = []
    
    for entry in feed.entries:
        try:
            pub_date = datetime(*entry.published_parsed[:6])
            if pub_date < cutoff:
                continue
                
            title = entry.title
            link = entry.link
            date_str = pub_date.strftime("%Y-%m-%d")
            print(f"   Processing: {date_str} → {title[:60]}...")
            
            soup = BeautifulSoup(entry.description, "html.parser")
            tables = soup.find_all("table")
            
            for table in tables:
                rows = table.find_all("tr")
                if not rows:
                    continue
                    
                headers = [cell.get_text(strip=True).lower() for cell in rows[0].find_all(["th", "td"])]
                
                if any("scenario" in h for h in headers) and any("entry" in h for h in headers):
                    for row in rows[1:]:
                        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                        if len(cells) < 5: 
                            continue
                        trade_rows.append({
                            "Date": date_str,
                            "Ticker": title.split()[0] if title.split() and title.split()[0].isupper() else "MULTI",
                            "Post_Title": title,
                            "Scenario": cells[0],
                            "Entry": cells[1],
                            "Stop_Loss": cells[2] if len(cells) > 2 else "",
                            "Targets": cells[3] if len(cells) > 3 else "",
                            "R_R_Ratio": cells[5] if len(cells) > 5 else "",
                            "Est_Probability": cells[6] if len(cells) > 6 else "",
                            "Link": link
                        })
        except:
            continue

    df = pd.DataFrame(trade_rows)
    print(f"Extracted {len(df)} trade setups")
    return df

def fetch_current_prices(tickers):
    print("Fetching current prices...")
    prices = {}
    for ticker in set(tickers):
        if ticker == "MULTI":
            continue
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if not hist.empty:
                prices[ticker] = round(hist['Close'].iloc[-1], 2)
                print(f"   {ticker}: ${prices[ticker]}")
            time.sleep(0.8)
        except Exception as e:
            print(f"   Failed to get price for {ticker}")
            prices[ticker] = None
    return prices

# ====================== MAIN ======================
if __name__ == "__main__":
    ny_time = datetime.now(ZoneInfo("America/New_York"))
    market_open = is_us_market_open()
    
    print(f"Starting Wild Swing Playbook Update - {ny_time.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"Market status: {'OPEN 🟢' if market_open else 'CLOSED 🔵 (using last known prices)'}")

    df = get_latest_playbook_plays()
    
    if df.empty:
        print("No recent plays found. Creating empty file...")
        df = pd.DataFrame(columns=["Date","Ticker","Post_Title","Scenario","Entry","Stop_Loss","Targets","R_R_Ratio","Est_Probability","Link","Current_Price","Price_Updated"])
    else:
        if market_open:
            print("🟢 Market open → Fetching fresh prices...")
            prices = fetch_current_prices(df["Ticker"].tolist())
        else:
            print("🔵 Market closed → Using last known prices from previous run")
            prices = load_last_known_prices()
        
        df["Current_Price"] = df["Ticker"].map(prices)
        df["Price_Updated"] = ny_time.strftime("%Y-%m-%d %H:%M")

    # Save files (always create today's dated files)
    today_str = ny_time.strftime("%Y-%m-%d")
    
    csv_filename = f"Master_Playbook_Database_{today_str}.csv"
    df.to_csv(csv_filename, index=False)
    print(f"Saved {csv_filename} ({len(df)} rows)")
    
    unique_tickers = sorted([t for t in df["Ticker"].unique() if t != "MULTI" and pd.notna(t)])
    tv_filename = f"Playbook_Watchlist_Import_{today_str}.txt"
    with open(tv_filename, "w") as f:
        f.write(",".join(unique_tickers))
    print(f"Saved {tv_filename} ({len(unique_tickers)} tickers)")
    
    print("✅ Playbook update completed successfully!")
