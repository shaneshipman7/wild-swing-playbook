import feedparser
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import time

# ================== CONFIG ==================
DAYS_BACK = 7
BLOG_RSS = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss"
# ============================================

def get_latest_playbook_plays():
    print("🔍 Checking Wild Swing Trades for latest plays...")
    
    feed = feedparser.parse(BLOG_RSS)
    cutoff = datetime.now() - timedelta(days=DAYS_BACK)
    
    trade_rows = []
    playbooks = []

    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6])
        if pub_date < cutoff:
            continue
            
        html_content = entry.description
        soup = BeautifulSoup(html_content, "html.parser")
        markdown_content = md(str(soup), heading_style="ATX")
        
        title = entry.title
        link = entry.link
        date_str = pub_date.strftime("%Y-%m-%d")
        
        playbooks.append({
            "title": title,
            "date": pub_date.strftime("%B %d, %Y"),
            "link": link,
            "content": markdown_content
        })
        
        # === TABLE PARSER ===
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
            
            elif any("ticker" in h for h in headers) and any("entry" in h for h in headers):
                for row in rows[1:]:
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if len(cells) < 4: continue
                    trade_rows.append({
                        "Date": date_str, 
                        "Ticker": cells[0].replace("**", "").strip(),
                        "Post_Title": title, 
                        "Scenario": "Rebound Play",
                        "Entry": cells[1], 
                        "Stop_Loss": "See full post (~12% typical)",
                        "Targets": f"Cons: {cells[2]} | Bull: {cells[3]}" if len(cells) > 3 else cells[2],
                        "R_R_Ratio": cells[4] if len(cells) > 4 else "",
                        "Est_Probability": cells[5] if len(cells) > 5 else "",
                        "Link": link
                    })

    return pd.DataFrame(trade_rows), playbooks


def get_conviction_score(row):
    scenario = str(row.get("Scenario", "")).lower()
    rr_str = str(row.get("R_R_Ratio", "")).lower()
    score = 0
    if any(x in scenario for x in ["primary", "bullish pullback"]):
        score += 40
    elif "breakout" in scenario or "rebound" in scenario:
        score += 35
    else:
        score += 20
    if any(x in rr_str for x in ["5", "4", "1:5", "1:4"]):
        score += 30
    elif any(x in rr_str for x in ["3", "2.5", "1:3", "1:2.5"]):
        score += 20
    elif "2" in rr_str:
        score += 10
    return "🔥 HIGH" if score >= 65 else "⚡ MEDIUM" if score >= 45 else "📉 LOW"


def fetch_current_prices(tickers):
    print("📈 Fetching current prices...")
    prices = {}
    for ticker in set(tickers):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if not hist.empty:
                prices[ticker] = round(hist['Close'].iloc[-1], 2)
            time.sleep(0.6)
        except:
            prices[ticker] = None
    return prices


def print_pretty_alerts(df):
    if df.empty:
        print("✅ No plays found in the last", DAYS_BACK, "days.")
        return
    
    print(f"\n🚨 {len(df)} LATEST TRADE ALERTS from Wild Swing Trades\n")
    for _, row in df.iterrows():
        score = get_conviction_score(row)
        print("═" * 70)
        print(f"📌 {row['Ticker']}   |   {row['Scenario']}")
        print(f"📅 {row['Date']}     |   Conviction: {score}")
        print(f"🔑 Entry     →  {row['Entry']}")
        print(f"🛑 Stop      →  {row['Stop_Loss']}")
        print(f"🎯 Targets   →  {row['Targets']}")
        if row.get("R_R_Ratio"):
            print(f"📊 R:R       →  {row['R_R_Ratio']}")
        print(f"🔗 {row['Link']}")
        print()


# ====================== MAIN ======================
if __name__ == "__main__":
    df, playbooks = get_latest_playbook_plays()
    
    print_pretty_alerts(df)
    
    if not df.empty:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Add current prices
        prices = fetch_current_prices(df["Ticker"].tolist())
        df["Current_Price"] = df["Ticker"].map(prices)
        df["Price_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Save files
        csv_filename = f"Master_Playbook_Database_{today_str}.csv"
        df.to_csv(csv_filename, index=False)
        
        # TradingView Watchlist
        unique_tickers = sorted(df["Ticker"].unique())
        tv_filename = f"Playbook_Watchlist_Import_{today_str}.txt"
        with open(tv_filename, "w") as f:
            f.write(",".join(unique_tickers))
        
        print(f"\n✅ Success!")
        print(f"   📊 CSV Database → {csv_filename} ({len(df)} rows)")
        print(f"   📋 TradingView file → {tv_filename} ({len(unique_tickers)} tickers)")
        print(f"   📈 Prices updated for {sum(1 for v in prices.values() if v is not None)} tickers")