import feedparser
from bs4 import BeautifulSoup, Tag
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Optional
import argparse

FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss&max-results=30"
LOOKBACK_DAYS = 12

def extract_ticker(text: str) -> Optional[str]:
    match = re.search(r'\$([A-Z]{2,6})\b', text)
    return match.group(1).upper() if match else None

def find_setup_tables(soup: BeautifulSoup) -> List[Tag]:
    """More flexible table finder for Markdown-style tables."""
    tables = soup.find_all("table")
    good_tables = []
    for table in tables:
        # Get all rows
        rows = table.find_all("tr")
        if not rows:
            continue

        # Check first row for header-like content (works for both <th> and <td>)
        first_row_text = " ".join(cell.get_text(strip=True).lower() for cell in rows[0].find_all(["th", "td"]))
        
        signals = sum(1 for word in ["entry", "stop", "target", "conviction", "risk", "reward", "probability"] 
                      if word in first_row_text)
        
        if signals >= 2:
            good_tables.append(table)
    return good_tables

def normalize_header(header: str) -> str:
    h = header.lower().strip()
    if "entry" in h: return "Entry"
    if "stop" in h or "invalidation" in h: return "Stop_Loss"
    if "target 1" in h or h == "t1": return "Target_1"
    if "target 2" in h or h == "t2": return "Target_2"
    if "target 3" in h or h == "t3": return "Target_3"
    if "prob" in h and "1" in h: return "Prob_T1"
    if "prob" in h and "2" in h: return "Prob_T2"
    if "risk" in h and "%" in h: return "Risk_Pct"
    if "reward" in h and "%" in h: return "Reward_Pct"
    if "risk" in h or "r:r" in h or "rr" in h: return "R_R"
    if "conviction" in h: return "Conviction"
    if "position" in h and "size" in h: return "Position_Size"
    if "time" in h and "horizon" in h: return "Time_Horizon"
    return header

def parse_table(table: Tag) -> List[Dict]:
    rows = table.find_all("tr")
    if not rows:
        return []

    # Get headers from first row (supports both <th> and <td>)
    header_cells = rows[0].find_all(["th", "td"])
    headers_raw = [cell.get_text(strip=True) for cell in header_cells]
    if not headers_raw:
        return []
    
    headers = [normalize_header(h) for h in headers_raw]

    records = []
    for tr in rows[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        row = {}
        for i, header in enumerate(headers):
            if i < len(cells):
                row[header] = cells[i]
        # Keep if it has at least one key field
        if any(row.get(k) for k in ["Entry", "Stop_Loss", "Target_1", "Conviction"]):
            records.append(row)
    return records

def extract_setups_from_text(soup: BeautifulSoup, title: str) -> List[Dict]:
    """Text extractor for Executive Summary style sections."""
    text = soup.get_text(separator=" ", strip=True)
    record = {}

    patterns = {
        "Entry": r"(?:Entry Zone|Entry)[:\s]*\$?([\d.,]+)",
        "Stop_Loss": r"(?:Stop Loss|Invalidation)[:\s]*\$?([\d.,]+)",
        "Target_1": r"(?:Target 1|Target_1)[:\s]*\$?([\d.,]+)",
        "Target_2": r"(?:Target 2|Target_2)[:\s]*\$?([\d.,]+)",
        "Conviction": r"(?:Conviction Score|Conviction)[:\s]*(\d+)\s*/\s*100",
        "Position_Size": r"(?:Position Size)[:\s]*([\d–\-]+%)",
        "Time_Horizon": r"(?:Time Horizon)[:\s]*([^\n]{3,30})",
        "R_R": r"(?:Risk / Reward|R:R)[:\s]*([\d\s:.,]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            record[key] = match.group(1).strip()

    if record and any(record.get(k) for k in ["Entry", "Stop_Loss", "Target_1", "Conviction"]):
        return [record]
    return []

def generate_playbook(debug: bool = False):
    print("Fetching blog feed...")
    feed = feedparser.parse(FEED_URL)
    all_records = []
    now = datetime.now()

    processed = 0
    skipped_no_data = 0

    for entry in feed.entries:
        try:
            pub_date = datetime(*entry.published_parsed[:6])
            if (now - pub_date).days > LOOKBACK_DAYS:
                continue

            processed += 1
            title = entry.title
            link = entry.link
            ticker = extract_ticker(title)
            if not ticker:
                continue

            content = entry.get("description", "") or entry.get("summary", "")
            soup = BeautifulSoup(content, "lxml")

            tables = find_setup_tables(soup)
            setups = []
            if tables:
                for table in tables:
                    setups.extend(parse_table(table))
            if not setups:
                setups = extract_setups_from_text(soup, title)

            if not setups:
                skipped_no_data += 1
                if debug:
                    print(f"  No usable data in: {title[:50]}")
                continue

            for s in setups:
                all_records.append({
                    "Date": pub_date.strftime("%Y-%m-%d"),
                    "Ticker": ticker,
                    "Title": title,
                    "Entry": s.get("Entry", ""),
                    "Stop_Loss": s.get("Stop_Loss", ""),
                    "Target_1": s.get("Target_1", ""),
                    "Target_2": s.get("Target_2", ""),
                    "Conviction": s.get("Conviction", ""),
                    "Position_Size": s.get("Position_Size", ""),
                    "Time_Horizon": s.get("Time_Horizon", ""),
                    "R_R": s.get("R_R", ""),
                    "Link": link,
                    "Status": "TRACKING",
                    "Generated_At": now.strftime("%Y-%m-%d %H:%M")
                })

        except Exception as e:
            if debug:
                print(f"Error on post: {e}")
            continue

    print(f"Processed {processed} posts | Extracted from {processed - skipped_no_data} posts")

    if not all_records:
        print("No records extracted.")
        return

    df = pd.DataFrame(all_records)
    df = df[df["Ticker"] != "MULTI"]

    filename = f"Master_Playbook_Database_{now.strftime('%Y-%m-%d')}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Generated {filename} with {len(df)} setups.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    generate_playbook(debug=args.debug)
