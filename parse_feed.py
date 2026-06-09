import xml.etree.ElementTree as ET
import re
import pandas as pd

def parse_atom_feed(feed_path):
    # Atom feeds use specific XML namespaces
    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
    
    try:
        tree = ET.parse(feed_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    playbooks = []
    
    # Loop through every blog post entry in the file
    for entry in root.findall('atom:entry', namespaces):
        title = entry.find('atom:title', namespaces).text
        
        # Look for the actual link to the blog post
        blog_url = ""
        for link in entry.findall('atom:link', namespaces):
            if link.attrib.get('rel') == 'alternate':
                blog_url = link.attrib.get('href')
                break
        
        # Get the text content of the post to search for metrics
        content_element = entry.find('atom:content', namespaces)
        content_text = content_element.text if content_element is not None else ""
        
        if not content_text:
            continue
            
        # --- METRIC EXTRACTION LOGIC ---
        # 1. Search for Win Probability / Win Rate (e.g., 62% or 55.5%)
        win_match = re.search(r'(?:win\s*rate|probability|win\s*prob).*?(\d+(?:\.\d+)?)\s*%', content_text, re.IGNORECASE)
        if win_match:
            win_probability = float(win_match.group(1)) / 100.0
        else:
            win_probability = 0.50 # Default baseline if not explicitly found
            
        # 2. Search for Average Return (e.g., 4.5% return, +3% avg return)
        return_match = re.search(r'(?:return|avg\s*return|profit).*?([+-]?\d+(?:\.\d+)?)\s*%', content_text, re.IGNORECASE)
        if return_match:
            avg_return = float(return_match.group(1))
        else:
            avg_return = 0.0 # Default baseline if not explicitly found
            
        # 3. Categorize Market Regime based on keywords in the text
        regime = "Trending"
        if "mean reversion" in content_text.lower() or "fade" in content_text.lower():
            regime = "Mean Reverting"
        elif "high vol" in content_text.lower() or "breakout" in content_text.lower():
            regime = "High Volatility"

        # Generate a clean ID based on the order
        play_id = f"WS-{len(playbooks) + 1:03d}"
        
        # Filter out system posts or empty titles that aren't actual trading plays
        if "template" not in title.lower() and blog_url:
            playbooks.append({
                "play_id": play_id,
                "name": title,
                "regime": regime,
                "win_probability": win_probability,
                "avg_return": avg_return,
                "blog_url": blog_url
            })
            
    # Save everything cleanly to your CSV file
    df = pd.DataFrame(playbooks)
    df.to_csv('playbooks.csv', index=False)
    print(f"Successfully processed {len(playbooks)} plays into playbooks.csv!")

# Run the parser on your uploaded file
parse_atom_feed('feed.atom')
