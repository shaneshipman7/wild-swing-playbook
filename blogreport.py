import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
import time
import os
import re

try:
    from polygon import RESTClient
except ImportError:
    RESTClient = None

# ================== CONFIG ==================
DAYS_BACK = 90
BLOG_RSS = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss"
# ============================================

def extract_ticker_from_title(title):
    """Robust ticker extraction prioritizing common patterns in your post titles like ($XPO), $XEL, etc.
    Falls back gracefully and heavily filters title noise so far fewer posts become MULTI."""
    if not title:
        return "MULTI"

    # 1. Highest priority: explicit ($TICKER) or $TICKER patterns (very common in your titles)
    for pattern in [
        r'\(\$?([A-Z]{2,5})\)',   # ($XPO) or (XPO)
        r'\$([A-Z]{2,5})\)',       # $XPO)
        r'\$([A-Z]{2,5})\b',       # $XPO 
        r'\(([A-Z]{2,5})\)',       # (XPO)
    ]:
        match = re.search(pattern, title)
        if match:
            t = match.group(1).upper()
            if t not in {'THE', 'AND', 'FOR', 'INC', 'LLC', 'CORP', 'LTD', 'LLP'}:
                return t

    # 2. Broader search for standalone uppercase ticker-like words (2-5 letters)
    common_words = {
        'THE', 'AND', 'FOR', 'WITH', 'FROM', 'INTO', 'OVER', 'AFTER', 'BELOW', 'ABOVE',
        'BREAK', 'OUT', 'LONG', 'SHORT', 'BUY', 'SELL', 'HOLD', 'WATCH', 'NAMES', 'STOCKS',
        'INC', 'LLC', 'CORP', 'GROUP', 'FUND', 'ENERGY', 'TECHNOLOGIES', 'HOLDINGS',
        'PARTNERS', 'ROBOTICS', 'SPACE', 'LOGIC', 'MACHINES', 'UNUSUAL', 'WISDOMTREE',
        'TRUE', 'EMERGING', 'MARKETS', 'DETAILED', 'ANALYSIS', 'POWERFUL', 'COMPANY',
        'SURGES', 'REBOUNDS', 'TRANSFORMS', 'FOLLOWING', 'MASSIVE', 'Q1', 'Q2', 'AI',
        'DRIVEN', 'EXPANSION', 'DEMAND', 'ACCELERATE', 'GROWTH', 'RESULTS', 'EARNINGS',
        'CONTRACTS', 'FUEL', 'BREAKOUT', 'PULLBACK', 'SUPPORT', 'HIGH', 'GROWTH', 'ERA',
        'NEW', 'INSTITUTIONAL', 'STRONG', 'INDUSTRY', 'MOMENTUM', 'STEADY', 'DRIVE',
        'INFRASTRUCTURE', 'DEFENSIVE', 'OUTSIDE', 'CHINA', 'GOVERNMENT', 'DRONE',
        'SPENDING', 'EXPECTATIONS', 'EXPLOSIVE', 'REVENUE', 'COVERING',
        'TRANSFORMATIVE', 'DEBT', 'DEAL', 'HIGH-PROFILE', 'DEFENSE', 'COUNTER-DRONE',
        'PARTNERSHIPS', 'ARGUS', 'INTERCEPTION', 'PHOTONICS', 'HARDWARE', 'BOOM',
        'INCREDIBLE', 'YEAR-OVER-YEAR', 'SURGE', 'ENTERPRISE', 'ADOPTION', 'FAILED',
        'BREAKDOWN', 'SWEEP', 'DEEPER', 'VALUE', 'DIP', 'CONSERVATIVE', 'AGGRESSIVE',
        'MEAN', 'REVERSION', 'RANGE', 'FADE', 'BOUNCE', 'FLUSH', 'SHELF', 'STRUCTURAL',
        'REVERSAL', 'ACCUMULATION', 'SCALP', 'QUICK', 'MOMENTUM', 'RESISTANCE',
        'CHANNEL', 'MACRO', 'BASE', 'ZLEMA', 'RECLAIM', 'SETUP', 'TRIGGERED', 'ACTIVE',
        'ZONE', 'CONTINUATION', 'EXPANSION', 'MEASURED', 'TARGET', 'MOVE', 'FLAG',
        'BULLISH', 'BEARISH', 'ELECTONIC', 'ARTS', 'LOOK', 'WHAT', 'YOU', 'DOING', 'ME',
        'SILVER', 'MARKET', 'UPDATE', 'COMMODITY', 'PRECIOUS', 'METALS', 'TRUST', 'ISHARES',
        'FROM', 'RANGE', 'TO', 'NEW', 'HIGHS', 'ON', 'STRONG', 'INDUSTRY', 'MOMENTUM',
        'INFRASTRUCTURE', 'DEFENSIVE', 'DEMAND', 'STEADY', 'BREAKOUT', 'TRUE', 'EMERGING',
        'OUTSIDE', 'CHINA', 'SURGES', 'GOVERNMENT', 'DRONE', 'SPENDING', 'EXPECTATIONS',
        'ACCELERATE', 'BREAKS', 'OUT', 'ABOVE', 'PRIOR', 'RANGES', 'EXPLOSIVE', 'REVENUE',
        'FOLLOWING', 'MASSIVE', 'Q1', 'OUTPERFORMANCE', 'HEAVY', 'SHORT', 'COVERING',
        'REBOUNDS', 'AS', 'AI-DRIVEN', 'MARKETING', 'DEMAND', 'TRANSFORMS', 'ITS', 'STORY',
        'WITH', 'STRATEGIC', 'CRITICAL', 'MINERALS', 'MERGER', 'HIGH-GROWTH', 'COMPANY',
        'ENTERING', 'NEW', 'INSTITUTIONAL', 'ERA', 'AFTER', 'THE', 'CORRECTION', 'INVESTORS',
        'ARE', 'WATCHING', 'FOR', 'NEXT', 'CATALYST', 'DOORDASH', 'EXPANSION', 'AND',
        'DELIVERY', 'AUTOMATION', 'MAJOR', 'SATELLITE', 'IMAGING', 'CONTRACTS', 'POWERFUL',
        'DEFENSE', 'CONTRACTS', 'DRONE', 'DEMAND', 'ENTERPRISE', 'ADOPTION', 'FUELS',
        'DELIVERS', 'BREAKOUT', 'Q1', 'RESULTS', 'WITH', 'NET', 'PROFITABILITY', 'AND',
        'TRANSFORMATIVE', 'DEBT', 'DEAL', 'IS', 'ANOTHER', 'TICKER', 'THAT', 'HAS',
        'COMPLETELY', 'TRANSFORMED', 'RECENTLY', 'DRIVEN', 'BY', 'HIGH-PROFILE',
        'DEFENSE', 'CONTRACTS', 'LIKE', 'COUNTER-DRONE', 'PARTNERSHIPS', 'WITH',
        'GERMANY', 'ARGUS', 'INTERCEPTION', 'HAS', 'HAD', 'MASSIVE', 'INSTITUTIONAL',
        'RUN', 'BECAUSE', 'OF', 'THE', 'PHOTONICS', 'AND', 'AI', 'HARDWARE', 'BOOM',
        'FOLLOWING', 'ITS', 'INCREDIBLE', 'YEAR-OVER-YEAR', 'REVENUE', 'SURGE',
        'FOLLOWING', 'A', 'MASSIVE', 'YEAR-OVER-YEAR', 'REVENUE', 'SURGE', 'IN', 'THEIR',
        'RECENT', 'Q2', 'EARNINGS', 'REPORT', 'SPURRED', 'BY', 'SUPPLY', 'SURGES', 'IN',
        'GLOBAL', 'COPPER', 'MARKETS', 'THE', 'STOCK', 'HAS', 'BROKEN', 'SIGNIFICANTLY',
        'OUT', 'OF', 'ITS', 'OLD', 'RANGE', 'A', 'POWERFUL', 'COMPANY', 'ELECTONIC',
        'ARTS', 'DETAILED', 'LOOK', 'SLV', 'WHAT', 'YOU', 'DOING', 'TO', 'ME'
    }
    matches = re.findall(r'\b([A-Z]{2,5})\b', title)
    for m in matches:
        if m not in common_words and len(m) >= 2:
            return m

    return "MULTI"

def fetch_previous_close_prices(tickers):
    print("Fetching previous close prices...")
    prices = {}
    polygon_key = os.getenv("POLYGON_API_KEY")
    client = RESTClient(polygon_key) if (polygon_key and RESTClient) else None

    for ticker in set(tickers):
        if ticker == "MULTI":
            continue
        price = None

        # Try Polygon first (more reliable for many tickers)
        if client:
            try:
                snap = client.get_snapshot("stocks", ticker)
                if snap and hasattr(snap, 'prev_day') and snap.prev_day and snap.prev_day.c:
                    price = round(snap.prev_day.c, 2)
                    print(f"   {ticker}: ${price} (Polygon)")
            except Exception as e:
                print(f"   Polygon error for {ticker}: {str(e)[:80]}")

        # Fallback to yfinance if Polygon didn't give a price
        if price is None:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="5d")
                if not hist.empty:
                    price = round(hist['Close'].iloc[-1], 2)
                    print(f"   {ticker}: ${price} (yfinance)")
                time.sleep(0.8)
            except Exception as e:
                print(f"   yfinance error for {ticker}: {str(e)[:80]}")

        prices[ticker] = price
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
                    ticker = extract_ticker_from_title(title)
                    for row in rows[1:]:
                        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                        if len(cells) < 5: 
                            continue
                        trade_rows.append({
                            "Date": date_str,
                            "Ticker": ticker,
                            "Post_Title": title,
                            "Scenario": cells[0],
                            "Entry": cells[1],
                            "Stop_Loss": cells[2] if len(cells) > 2 else "",
                            "Targets": cells[3] if len(cells) > 3 else "",
                            "R_R_Ratio": cells[5] if len(cells) > 5 else "",
                            "Est_Probability": cells[6] if len(cells) > 6 else "",
                            "Link": link,
                            "Status": "TRACKING"
                        })
        except:
            continue

    df = pd.DataFrame(trade_rows)
    print(f"Extracted {len(df)} total plays from the last {DAYS_BACK} days")
    return df

# ====================== MAIN ======================
if __name__ == "__main__":
    ny_time = datetime.now(ZoneInfo("America/New_York"))
    market_open = True  # simplified
    
    print(f"Starting Wild Swing Playbook Update - {ny_time.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"Market status: OPEN (using previous close prices)")

    df = get_latest_playbook_plays()
    
    if df.empty:
        df = pd.DataFrame(columns=["Date","Ticker","Post_Title","Scenario","Entry","Stop_Loss","Targets","R_R_Ratio","Est_Probability","Link","Current_Price","Price_Updated","Status"])
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
        "Price_Updated": "Data updated every 45 min",
        "Status": ""
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
