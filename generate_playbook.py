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
    """Find tables that contain real trade setup data (old format)."""
    tables = soup.find_all("table")
    good_tables = []
    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        header_str = " ".join(headers)
        signals = sum(1 for word in ["entry", "stop", "target", "probability", "risk", "conviction"] if word in header_str)
        if signals >= 2:
            good_tables.append(table)
    return good_tables

def normalize_header(header: str) -> str:
    h = header.lower().strip()
    if "entry" in h: return "Entry"
    if "stop" in h: return "Stop_Loss"
    if "target 1" in h or h == "t1": return "Target_1"
    if "target 2" in h or h == "t2": return "Target_2"
    if "prob" in h and ("1" in h or "t1" in h): return "Prob_T1"
    if "prob" in h and ("2" in h or "t2" in h): return "Prob_T2"
    if "risk" in h or "r:r" in h or "rr" in h: return "R_R"
    if "return" in h or "%" in h: return "Est_Return"
    if "conviction" in h: return "Conviction"
    return header

def parse_table(table: Tag) -> List[Dict]:
    headers_raw = [th.get_text(strip=True) for th in table.find_all("th")]
    if not headers_raw:
        return []
    headers = [normalize_header(h) for h in headers_raw]
    records = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 2: continue
        row = {}
        for i, header in enumerate(headers):
            if i < len(cells):
                row[header] = cells[i]
        if row.get("Entry") or row.get("Stop_Loss") or row.get("Target_1"):
            records.append(row)
    return records

# ===================== NEW: Flexible text-based extractor =====================
def extract_setups_from_text(soup: BeautifulSoup, title: str) -> List[Dict]:
    """Extract trade data from structured text when no table is found."""
    text = soup.get_text(separator="\n", strip=True)
    records = []

    patterns = {
        "Entry": r"(?:Entry|Entries)[:\s]*\$?([\d.,]+(?:\s*[-–]\s*\$?[\d.,]+)?)",
        "Stop_Loss": r"(?:Stop|Stop Loss|Invalidation)[:\s]*\$?([\d.,]+)",
        "Target_1": r"(?:Target\s*1|First Target|T1)[:\s]*\$?([\d.,]+)",
        "Target_2": r"(?:Target\s*2|Second Target|T2)[:\s]*\$?([\d.,]+)",
        "Conviction": r"(?:Conviction|Conv)[:\s]*(\d+)(?:/100)?",
        "R_R": r"(?:R:R|Risk[:/]?Reward|RR)[:\s]*([\d:.,]+)",
        "Position_Size": r"(?:Position Size|Size)[:\s]*([\d–\-]+%)",
        "Time_Horizon": r"(?:Time Horizon|Horizon|Hold Time)[:\s]*([^\n]+)",
        "Setup_Type": r"(?:Setup Type|Type|Bias)[:\s]*([^\n]+)",
    }

    record = {}
    found_any = False

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            record[key] = match.group(1).strip()
            found_any = True

    if found_any and (record.get("Entry") or record.get("Stop_Loss") or record.get("Target_1")):
        records.append(record)

    return records
# ==============================================================================

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
                if debug:
                    print(f"  No $TICKER in title: {title[:60]}")
                continue

            content = entry.get("description", "") or entry.get("summary", "")
            soup = BeautifulSoup(content, "lxml")

            # Try old table method first
            tables = find_setup_tables(soup)
            setups = []
            if tables:
                for table in tables:
                    setups.extend(parse_table(table))
            else:
                # Fallback to text extraction for current blog format
                setups = extract_setups_from_text(soup, title)

            if not setups:
                skipped_no_data += 1
                if debug:
                    print(f"  No usable setup data found in: {title[:60]}")
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
                    "Prob_T1": s.get("Prob_T1", ""),
                    "Prob_T2": s.get("Prob_T2", ""),
                    "R_R": s.get("R_R", ""),
                    "Est_Return": s.get("Est_Return", ""),
                    "Conviction": s.get("Conviction", ""),
                    "Position_Size": s.get("Position_Size", ""),
                    "Time_Horizon": s.get("Time_Horizon", ""),
                    "Setup_Type": s.get("Setup_Type", ""),
                    "Link": link,
                    "Status": "TRACKING",
                    "Generated_At": now.strftime("%Y-%m-%d %H:%M")
                })

        except Exception as e:
            if debug:
                print(f"Error on post '{title[:40]}': {e}")
            continue

    print(f"Processed {processed} posts | Extracted data from {processed - skipped_no_data} posts")

    if not all_records:
        print("No records extracted. Parser may need more tuning for current post format.")
        return

    df = pd.DataFrame(all_records)
    df = df[df["Ticker"] != "MULTI"]

    filename = f"Master_Playbook_Database_{now.strftime('%Y-%m-%d')}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Generated {filename} with {len(df)} setups.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Show detailed parsing info")
    args = parser.parse_args()
    generate_playbook(debug=args.debug)
