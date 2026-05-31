from datetime import datetime
import pandas as pd

print(f"🚀 Script started at {datetime.now()}")

# Create a simple test dataframe so we always have output
data = {
    "Date": ["2026-05-30"],
    "Ticker": ["TEST"],
    "Post_Title": ["Debug Test"],
    "Scenario": ["Manual Test"],
    "Entry": ["Test Entry"],
    "Stop_Loss": ["Test Stop"],
    "Targets": ["Test Targets"],
    "R_R_Ratio": ["1:2"],
    "Est_Probability": ["60%"],
    "Link": ["https://example.com"]
}

df = pd.DataFrame(data)

today_str = datetime.now().strftime("%Y-%m-%d")

csv_filename = f"Master_Playbook_Database_{today_str}.csv"
df.to_csv(csv_filename, index=False)
print(f"✅ Created {csv_filename}")

tv_filename = f"Playbook_Watchlist_Import_{today_str}.txt"
with open(tv_filename, "w") as f:
    f.write("TEST")

print("🎉 Script finished successfully!")
