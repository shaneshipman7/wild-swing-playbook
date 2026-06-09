import feedparser
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import os

FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss&max-results=30"
LOOKBACK_DAYS = 14

def parse_setup_table(soup):
    """Try to extract data from the Trade Setup Table in the post."""
    tables = soup.find_all("table")
    setups = []

    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not headers:
            continue

        # Look for key columns we care about
        header_text = " ".join(headers)
        if "entry" not in header_text and "stop" not in header_text:
            continue

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 4:
                continue

            # Basic mapping (adjust as your table evolves)
            setup = {
                "Entry": cells[0] if len(cells) > 0 else "",
                "Stop_Loss": cells[1] if len(cells) > 1 else "",
                "Target_1": cells[2] if len(cells) > 2 else "",
                "Prob_T1": cells[3] if len(cells) > 3 else "",
            }
            setups.append(setup)

    return setups

def extract_ticker(title):
    match = re.search(r'\$([A-Z]{2,5})\b', title)
    return match.group(1).upper() if match else None

def generate_playbook_csv():
    print("Fetching blog feed...")
    feed = feedparser.parse(FEED_URL)
    all_setups = []
    now = datetime.now()

    for entry in feed.entries:
        try:
            pub_date = datetime(*entry.published_parsed[:6])
            if (now - pub_date).days > LOOKBACK_DAYS:
                continue

            title = entry.title
            link = entry.link
            ticker = extract_ticker(title)
            if not ticker:
                continue

            content = entry.get("description", "") or entry.get("summary", "")
            soup = BeautifulSoup(content, "lxml")

            setups = parse_setup_table(soup)
            if not setups:
                continue  # skip posts without a proper table for now

            for s in setups:
                all_setups.append({
                    "Date": pub_date.strftime("%Y-%m-%d"),
                    "Ticker": ticker,
                    "Title": title,
                    "Entry": s.get("Entry", ""),
                    "Stop_Loss": s.get("Stop_Loss", ""),
                    "Targets": s.get("Target_1", ""),
                    "Prob": s.get("Prob_T1", ""),
                    "Link": link,
                    "Status": "TRACKING"
                })

        except Exception as e:
            print(f"Error processing post: {e}")
            continue

    if not all_setups:
        print("No setups found with tables in the lookback window.")
        return

    df = pd.DataFrame(all_setups)

    # Basic cleaning
    df = df[df['Ticker'] != 'MULTI']
    df = df[df['Entry'] != '']

    filename = f"Master_Playbook_Database_{now.strftime('%Y-%m-%d')}.csv"
    df.to_csv(filename, index=False)
    print(f"Generated {filename} with {len(df)} setups.")

if __name__ == "__main__":
    generate_playbook_csv()
