import feedparser
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import time
import os

# ================== CONFIG ==================
DAYS_BACK = 7
BLOG_RSS = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss"
# ============================================

print(f"🚀 Starting playbook update at {datetime.now()}")

def get_latest_playbook_plays():
    print("🔍 Fetching RSS feed...")
    feed = feedparser.parse(BLOG_RSS)
    print(f"   Found {len(feed.entries)} total posts")
    
    cutoff = datetime.now() - timedelta(days=DAYS_BACK)
    trade_rows = []
    
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6])
        if pub_date < cutoff:
            continue
            
        title = entry.title
        link = entry.link
        date_str = pub_date.strftime("%Y-%m-%d")
        print(f"   Processing: {date_str} - {title}")
        
        soup = BeautifulSoup(entry.description, "html.parser")
        tables = soup.find_all("table")
        
        for table in tables:
            rows = table.find_all("tr")
            if not rows: continue
            headers = [cell.get_text(strip=True).lower() for cell in rows[0].find_all(["th", "td"])]
            
            if any("scenario" in h for h in headers) and any("entry" in h for h in headers):
                for row in rows[1:]:
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if len(cells) < 7: continue
                    trade_rows.append({
                        "Date": date_str, 
                        "Ticker": title.split()[0] if title.split() and title.split()[0].isupper() else "MULTI",
                        "Post_Title": title, 
                        "Scenario": cells[0], 
                        "Entry": cells[1],
                        "Stop_Loss": cells[2], 
                        "Targets": cells[3],
                        "R_R_Ratio": cells[5] if len(cells) > 5 else "",
                        "Est_Probability": cells[6] if len(cells) > 6 else "",
                        "Link": link
                    })

    df = pd.DataFrame(trade_rows)
    print(f"✅ Extracted {len(df)} trade rows")
    return df


def fetch_current_prices(tickers):
    print("📈 Fetching prices...")
    prices = {}
    for ticker in set(tickers):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if not hist.empty:
                prices[ticker] = round(hist['Close'].iloc[-1], 2)
                print(f"   {ticker}: ${prices[ticker]}")
            time.sleep(0.7)
        except:
            prices[ticker] = None
    return prices


# ====================== MAIN ======================
if __name__ == "__main__":
    df = get_latest_playbook_plays()   # Simplified - removed unused playbooks part
    
    if df.empty:
        print("⚠️ No plays found in last 7 days. Creating empty files anyway...")
        df = pd.DataFrame(columns=["Date","Ticker","Post_Title","Scenario","Entry","Stop_Loss","Targets","R_R_Ratio","Est_Probability","Link"])
    
    # Add prices
    if not df.empty:
        prices = fetch_current_prices(df["Ticker"].tolist())
        df["Current_Price"] = df["Ticker"].map(prices)
        df["Price_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Always save files
    csv_filename = f"Master_Playbook_Database_{today_str}.csv"
    df.to_csv(csv_filename, index=False)
    print(f"💾 Saved {csv_filename} ({len(df)}
