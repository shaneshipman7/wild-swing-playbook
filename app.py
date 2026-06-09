# =============================================================================
# Grok API Ticker Analysis Script - Real-Time Search & Blogger Ready
# Fixed for xAI Responses API (June 2026) - Real-Time Date Automation Included
# =============================================================================

from google.colab import userdata, files
import os
import time
import re
from datetime import datetime
import requests
from typing import List, Dict

# ----------------------------- API SETUP -----------------------------
try:
    GROK_API_KEY = userdata.get("GROK_API_KEY")
except Exception:
    GROK_API_KEY = os.getenv("GROK_API_KEY")

if not GROK_API_KEY:
    raise ValueError("❌ GROK_API_KEY not found in Colab Secrets! Add it under the key icon.")

API_URL = "https://api.x.ai/v1/responses"
MODEL_TAG = "grok-4.3"

SYSTEM_PROMPT = """You are a highly experienced professional swing trader and market analyst with 20+ years of experience.
You combine technical analysis (ICT, Wyckoff, volume profile, order flow), catalysts, sentiment, and strict risk management.

CRITICAL DATA RULES:
1. Always use the web_search tool to get the absolute latest real-time stock price and data before answering.
2. Base every valuation, support/resistance, and scenario strictly on current real-world prices. Never hallucinate old levels.
3. Provide realistic, qualitatively derived probability estimates for all trade targets based on technical confluence, market regime, and ATR."""

# ----------------------------- CORE API CALL (Responses API) -----------------------------
def grok_api_call(messages: List[Dict], temperature=0.65, max_tokens=2000) -> str:
    input_payload = messages if isinstance(messages, list) else [messages]

    payload = {
        "model": MODEL_TAG,
        "input": input_payload,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "tools": [{"type": "web_search"}],
        "tool_choice": "auto"
    }

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(API_URL, json=payload, headers=headers, timeout=180)

    if response.status_code != 200:
        print("❌ API Error Details:", response.text)
        response.raise_for_status()

    data = response.json()

    try:
        output = data.get("output", [])
        content_parts = []
        for item in output:
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        content_parts.append(content.get("text", ""))
        return "\n".join(content_parts) or "No content returned."
    except Exception as e:
        print("⚠️ Response parsing issue:", e)
        return str(data)

# ----------------------------- HTML CLEANER -----------------------------
def clean_html_output(raw_content: str) -> str:
    clean = raw_content.strip()
    clean = re.sub(r'^```html\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^```\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s*```$', '', clean, flags=re.IGNORECASE)
    return clean.strip()

# ----------------------------- ANALYSIS STEPS -----------------------------
def step_1_technicals(ticker: str) -> str:
    return f"Research the following ticker: {ticker}. Use your web_search tool to find the exact current live stock price right now. Review the current real-world RSI, EMA, volume profile distribution, and chart resistance/support lines based on today's exact price action. Does it look like a valid technical swing trade setup right now?"

def step_2_sentiment(ticker: str) -> str:
    return f"Based on the technical profile for {ticker}, what is the current social sentiment among prominent Twitter/X traders over the past 48-72 hours?"

def step_3_trade_table() -> str:
    return """Based on the real-world current price found via web search, provide a clean Markdown table of potential trade setups.

You must include an explicit technical estimation of probability for your targets being hit.
The table MUST include exactly these columns:
| Entry Zone | Stop Loss | Target 1 | Target 1 Probability | Target 2 | Target 2 Probability | Estimated % Returns | Risk-to-Reward (R:R) Ratio |

**CRITICAL FORMATTING RULES:**
- In the **Target 1 Probability** and **Target 2 Probability** columns, put the % sign directly in every data row (e.g. 65%, 42%).
- In the **Estimated % Returns** column, always include the % sign in every row (e.g. +85%, -18%, +120%).
- Do NOT put any % signs in the column headers.
- Keep numbers clean and properly formatted.

Directly below the table, write a brief, 2-sentence technical justification explaining why you assigned those specific percentage probabilities (e.g., citing volume profile gaps, nearby key resistance levels, or market trend strength)."""

def step_4_html_blog(ticker: str) -> str:
    current_date_str = datetime.now().strftime("%B %d, %Y")

    return f"""Write a full professional, comprehensive blog post in clean HTML format optimized for Blogger for {ticker}.

CRITICAL DATE RULE: You must explicitly write the text "{current_date_str}" as the publication/analysis date in the blog header.

Blogger-Specific Design Rules:
- Wrap everything inside <div class="blogger-post-wrapper">...</div>
- Include a <style> block with modern CSS targeted only at .blogger-post-wrapper
- For tables: wrap in .table-container with overflow-x:auto and min-width:700px on the table
- Ensure the table explicitly displays the Target Probabilities columns with the % signs.
- Use clean typography, amber risk disclaimer boxes, zebra striping on tables
- Include risk disclaimers at top and bottom.
- Link {ticker} to https://www.tradingview.com/symbols/{ticker}/ (target="_blank")
- Use a compelling title matching the technical thesis.

Output ONLY the raw HTML (starting with the <div class="blogger-post-wrapper">). No extra commentary."""

# ----------------------------- MAIN PIPELINE -----------------------------
def analyze_tickers(tickers: List[str], delay: int = 12):
    results = {}
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

    print(f"🚀 Starting multi-step Grok analysis for {len(tickers)} tickers...\n")

    for i, ticker in enumerate(tickers, 1):
        ticker = ticker.upper().replace("$", "").strip()
        print(f"[{i}/{len(tickers)}] 🔄 Processing {ticker}...")

        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

        try:
            for step_func in [step_1_technicals, step_2_sentiment, step_3_trade_table]:
                user_msg = step_func(ticker) if step_func != step_3_trade_table else step_3_trade_table()
                conversation.append({"role": "user", "content": user_msg})
                reply = grok_api_call(conversation)
                conversation.append({"role": "assistant", "content": reply})
                print(f"  ↳ Step completed")

            conversation.append({"role": "user", "content": step_4_html_blog(ticker)})
            raw_html = grok_api_call(conversation, temperature=0.2, max_tokens=4000)
            final_html = clean_html_output(raw_html)

            results[ticker] = final_html

            filename = f"{ticker}_Live_Blogger_Post_{timestamp}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(final_html)

            print(f"✅ {ticker} completed → {filename}\n")

            if i < len(tickers):
                time.sleep(delay)

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            results[ticker] = f"<h1>Error on {ticker}</h1><p>{str(e)}</p>"

    master_file = f"MASTER_LIVE_BLOGGER_EXPORT_{timestamp}.html"
    with open(master_file, "w", encoding="utf-8") as f:
        for ticker, content in results.items():
            f.write(f"\n{content}\n\n<hr style='margin: 40px 0;'>\n\n")

    print(f"\n🎉 All done! Master export: {master_file}")
    files.download(master_file)

# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    try:
        tickers_input = input("Enter tickers separated by commas (e.g. SMR, OKLO, NNE, HUBC): ")
    except:
        tickers_input = "GEV, BWXT"

    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

    if tickers:
        analyze_tickers(tickers, delay=12)
    else:
        print("No tickers provided.")
