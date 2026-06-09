import feedparser
from bs4 import BeautifulSoup, Tag
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict

FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss&max-results=25"
LOOKBACK_DAYS = 10

def extract_ticker(text: str) -> str:
    match = re.search(r'\$([A-Z]{2,6})\b', text)
    return match.group(1).upper() if match else ""

def parse_number(val: str) -> float:
    nums = re.findall(r"[\d.]+", str(val))
    return float(nums[0]) if nums else 0.0

def find_setup_tables(soup: BeautifulSoup) -> List[Tag]:
    """Find tables that look like trade setup tables."""
    tables = soup.find_all("table")
    good_tables = []
    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        header_str = " ".join(headers)
        if "entry" in header_str or "stop" in header_str or "target" in header_str:
            good_tables.append(table)
    return good_tables

def parse_table(table: Tag) -> List[Dict]:
    """Parse a trade setup table into list of dicts."""
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if not headers:
        return []

    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header row
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 3:
            continue

        row_data = {}
        for i, header in enumerate(headers):
            if i < len(cells):
                row_data[header] = cells[i]

        # Normalize common fields
        setup = {
            "Entry": row_data.get("Entry Zone", row_data.get("Entry", "")),
            "Stop_Loss": row_data.get("Stop Loss", row_data.get("Stop", "")),
            "Target_1": row_data.get("Target 1", row_data.get("T1", "")),
            "Target_2": row_data.get("Target 2", row_data.get("T2", "")),
            "Prob_T1": row_data.get("Target 1 Probability", row_data.get("Prob T1", "")),
            "Prob_T2": row_data.get("Target 2 Probability", row_data.get("Prob T2", "")),
            "R_R": row_data.get("Risk-to-Reward (R:R) Ratio", row_data.get("R:R", "")),
            "Est_Return": row_data.get("Estimated % Returns", ""),
        }
        rows.append(setup)
    return rows

def generate_csv():
    print("Fetching feed...")
    feed = feedparser.parse(FEED_URL)
    records = []
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

            tables = find_setup_tables(soup)
            if not tables:
                continue

            for table in tables:
                setups = parse_table(table)
                for s in setups:
                    records.append({
                        "Date": pub_date.strftime("%Y-%m-%d"),
                        "Ticker": ticker,
                        "Title": title,
                        "Entry": s["Entry"],
                        "Stop_Loss": s["Stop_Loss"],
                        "Target_1": s["Target_1"],
                        "Target_2": s["Target_2"],
                        "Prob_T1": s["Prob_T1"],
                        "Prob_T2": s["Prob_T2"],
                        "R_R": s["R_R"],
                        "Est_Return": s["Est_Return"],
                        "Link": link,
                        "Status": "TRACKING"
                    })

        except Exception as e:
            print(f"Skipped post due to error: {e}")
            continue

    if not records:
        print("No records extracted. Your tables might still need slight adjustment or the parser needs tuning.")
        return

    df = pd.DataFrame(records)
    # Basic cleanup
    df = df[df["Ticker"] != "MULTI"]
    df = df[df["Entry"] != ""]

    filename = f"Master_Playbook_Database_{now.strftime('%Y-%m-%d')}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Generated {filename} with {len(df)} clean setups.")

if __name__ == "__main__":
    generate_csv()
