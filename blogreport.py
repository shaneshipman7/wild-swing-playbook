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
DAYS_BACK = 30
BLOG_RSS = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss"
# ============================================

def is_us_market_open():
    ny_time = datetime.now(ZoneInfo("America/New_York"))
    if ny_time.weekday() >= 5:
        return False
    if ny_time.hour < 9 or (ny_time.hour == 9 and ny_time.minute < 30):
        return False
    if ny_time.hour >= 16:
        return False
    return True

def fetch_previous_close_prices(tickers):
    print("Fetching previous close prices...")
    prices = {}
    for ticker in set(tickers):
        if ticker == "MULTI":
            continue
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                prices[ticker] = round(hist['Close'].iloc[-1], 2)
                print(f"   {ticker}: ${prices[ticker]} (previous close)")
            time.sleep(0.8)
        except:
            print(f"   Failed to get previous close for {ticker}")
            prices[ticker] = None
    return prices

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
    print(f"Extracted {len(df)} trade setups from last {DAYS_BACK} days")
    return df

# ====================== MAIN ======================
if __name__ == "__main__":
    ny_time = datetime.now(ZoneInfo("America/New_York"))
    market_open = is_us_market_open()
    
    print(f"Starting Wild Swing Playbook Update - {ny_time.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"Market status: {'OPEN 🟢' if market_open else 'CLOSED 🔵 (using previous close prices)'}")

    df = get_latest_playbook_plays()
    
    if df.empty:
        df = pd.DataFrame(columns=["Date","Ticker","Post_Title","Scenario","Entry","Stop_Loss","Targets","R_R_Ratio","Est_Probability","Link","Current_Price","Price_Updated"])
    else:
        prices = fetch_previous_close_prices(df["Ticker"].tolist())
        df["Current_Price"] = df["Ticker"].map(prices)
        df["Price_Updated"] = ny_time.strftime("%Y-%m-%d %H:%M")

    # Disclaimer row
    disclaimer_row = pd.DataFrame([{
        "Date": "⚠️ DISCLAIMER",
        "Ticker": "EXPERIMENTAL DATA ONLY",
        "Post_Title": "Accuracy NOT guaranteed • NOT financial advice • Use at your own risk",
        "Scenario": "See README for full details",
        "Entry": "",
        "Stop_Loss": "",
        "Targets": "",
        "R_R_Ratio": "",
        "Est_Probability": "",
        "Link": "https://github.com/shaneshipman7/wild-swing-playbook",
        "Current_Price": "",
        "Price_Updated": "Data updated every 45 min"
    }])
    df = pd.concat([disclaimer_row, df], ignore_index=True)

    # Save files
    today_str = ny_time.strftime("%Y-%m-%d")
    csv_filename = f"Master_Playbook_Database_{today_str}.csv"
    df.to_csv(csv_filename, index=False)
    print(f"Saved {csv_filename} ({len(df)-1} plays + disclaimer)")

    unique_tickers = sorted([t for t in df["Ticker"].unique() if t != "MULTI" and pd.notna(t) and t != "EXPERIMENTAL DATA ONLY"])
    tv_filename = f"Playbook_Watchlist_Import_{today_str}.txt"
    with open(tv_filename, "w") as f:
        f.write(",".join(unique_tickers))
    print(f"Saved {tv_filename} ({len(unique_tickers)} tickers)")
    
    print("✅ Playbook update completed successfully!")
