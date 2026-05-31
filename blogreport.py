import feedparser
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from datetime import datetime, timedelta
import os
import pandas as pd

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
                        "Date": date_str, "Ticker": title.split()[0] if title.split() and title.split()[0].isupper() else "MULTI",
                        "Post_Title": title, "Scenario": cells[0], "Entry": cells[1],
                        "Stop_Loss": cells[2], "Targets": cells[3],
                        "R_R_Ratio": cells[5] if len(cells) > 5 else "",
                        "Est_Probability": cells[6] if len(cells) > 6 else "",
                        "Link": link
                    })
            
            elif any("ticker" in h for h in headers) and any("entry" in h for h in headers):
                for row in rows[1:]:
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if len(cells) < 4: continue
                    trade_rows.append({
                        "Date": date_str, "Ticker": cells[0].replace("**", "").strip(),
                        "Post_Title": title, "Scenario": "Rebound Play",
                        "Entry": cells[1], "Stop_Loss": "See full post (~12% typical)",
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
    
    # Pretty alerts (now shows every run)
    print_pretty_alerts(df)
    
    # Your original file outputs
    if not df.empty:
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Markdown Playbook
        playbooks.sort(key=lambda x: x["date"], reverse=True)
        md_filename = f"Master_Swing_Trading_Playbook_{today_str}.md"
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(f"# Master Swing Trading Playbook - {datetime.now().strftime('%B %d, %Y')}\n\n")
            f.write(f"**Generated from Wild Swing Trades**  \n")
            f.write(f"Last {DAYS_BACK} days • {len(playbooks)} playbooks\n\n")
            for i, pb in enumerate(playbooks, 1):
                anchor = pb['title'].lower().replace(' ', '-').replace('.', '')
                f.write(f"{i}. [{pb['title']}](#{anchor})\n")
            f.write("\n---\n\n")
            for pb in playbooks:
                anchor = pb['title'].lower().replace(' ', '-').replace('.', '')
                f.write(f"<a id=\"{anchor}\"></a>\n")
                f.write(f"## {pb['title']}\n\n")
                f.write(f"**Published:** {pb['date']}  \n")
                f.write(f"**Original post:** [{pb['link']}]({pb['link']})\n\n")
                f.write(pb['content'])
                f.write("\n\n---\n\n")
        
        # CSV Database
        csv_filename = f"Master_Playbook_Database_{today_str}.csv"
        df.to_csv(csv_filename, index=False)
        
        # TradingView Watchlist
        unique_tickers = sorted(df["Ticker"].unique())
        tv_filename = f"Playbook_Watchlist_Import_{today_str}.txt"
        with open(tv_filename, "w") as f:
            f.write(",".join(unique_tickers))
        
        print(f"✅ Success!")
        print(f"   📄 Markdown → {md_filename}")
        print(f"   📊 Database CSV → {csv_filename} ({len(df)} rows)")
        print(f"   📋 TradingView file → {tv_filename} ({len(unique_tickers)} unique tickers)")
        print("   Ready to import in 1 click!")