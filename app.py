@st.cache_data(ttl=1800, show_spinner="Syncing latest plays from your blog...")
def get_raw_playbook(lookback_days: int = 30):
    FEED_URL = "https://wildswingtrades.blogspot.com/feeds/posts/default?alt=rss&max-results=50"
    try:
        feed = feedparser.parse(FEED_URL)
        if not feed.entries:
            raise ValueError("Empty feed")

        all_plays = []
        seen_tickers = set()
        now = datetime.now()

        for entry in feed.entries:
            try:
                title = entry.get("title", "")
                link = entry.get("link", "")
                pub_parsed = entry.get("published_parsed")
                pub_date = datetime(*pub_parsed[:6]) if pub_parsed else now
                days_old = (now - pub_date).days
                if days_old > lookback_days:
                    continue

                content_html = entry.get("description", "") or entry.get("summary", "")
                soup = BeautifulSoup(content_html, "lxml")
                full_text = soup.get_text(separator=" ", strip=True)
                text_lower = full_text.lower()

                # Ticker extraction
                ticker_match = re.search(r'\$([A-Z]{2,5})\b', title)
                if not ticker_match:
                    ticker_match = re.search(r'\b([A-Z]{2,5})\b(?=.*(?:stock|inc|holdings|group|etf|fund))', title, re.IGNORECASE)
                if not ticker_match:
                    continue
                ticker = ticker_match.group(1).upper()
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                # Scenario cleaning
                scenario_base = title.split(":")[0].strip() if ":" in title else title[:60]
                scenario_base = re.sub(r'\$?[A-Z]{2,5}\b|\s*\(.*?\)\s*', '', scenario_base)
                scenario_base = re.sub(r'\b(Inc|Corp|Corporation|Holdings|Group|Technologies|Systems|Company|Inc\.|Ltd\.?|LLC)\b', '', scenario_base, flags=re.IGNORECASE)
                scenario_base = re.sub(r'\s+', ' ', scenario_base).strip()
                if len(scenario_base) > 45:
                    scenario_base = scenario_base[:45].rsplit(' ', 1)[0]
                if not scenario_base:
                    scenario_base = "Play"

                direction = "Short" if any(kw in text_lower for kw in ["short", "bearish", "resistance play", "failed breakout short"]) else "Long"

                # Price / probability parsing
                def find_price(keyword_regex, text, fallback=None):
                    pattern = rf'{keyword_regex}[^.]*?\$?(\d{{1,4}}(?:\.\d{{1,2}})?)'
                    m = re.search(pattern, text, re.IGNORECASE)
                    if m:
                        try:
                            val = float(m.group(1))
                            if 0.5 < val < 1000:
                                return val
                        except:
                            pass
                    return fallback

                prob_t1, prob_t2 = "N/A", "N/A"
                t1_match = re.search(r'(?:target\s*1|t1)[^.%]*?(\d{2})\s*%', text_lower)
                t2_match = re.search(r'(?:target\s*2|t2)[^.%]*?(\d{2})\s*%', text_lower)
                if t1_match:
                    prob_t1 = f"{t1_match.group(1)}%"
                if t2_match:
                    prob_t2 = f"{t2_match.group(1)}%"

                if prob_t1 == "N/A":
                    all_percentages = re.findall(r'(\d{2})\s*%', text_lower)
                    if len(all_percentages) >= 1:
                        prob_t1 = f"{all_percentages[0]}%"
                    if len(all_percentages) >= 2:
                        prob_t2 = f"{all_percentages[1]}%"

                current_price = find_price(r'(?:near|around|consolidat|trading at|close|currently)', full_text)
                support = find_price(r'support', full_text, current_price * 0.96 if current_price else None)
                resistance = find_price(r'(?:resistance|target|breakout to|upside to)', full_text)

                if not resistance and current_price:
                    all_prices = [float(p) for p in re.findall(r'\$?(\d{1,4}(?:\.\d{{1,2}})?)', full_text)]
                    higher = [p for p in all_prices if p > (current_price or 0) * 1.05]
                    if higher:
                        resistance = max(higher[:5])

                base_status = "⏳ Monitoring Setup"
                if any(kw in text_lower for kw in ["break out", "breaks out", "surge", "explosive", "reclaim", "new high"]):
                    base_status = "🟢 Momentum / Breakout Setup"
                elif any(kw in text_lower for kw in ["pullback", "dip buy", "value support", "consolidat"]):
                    base_status = "🟢 IN ENTRY ZONE"
                if days_old <= 1:
                    base_status = "🆕 Fresh • " + base_status

                def make_zone(price, spread=0.018):
                    if not price or price <= 0:
                        return "TBD"
                    low = round(price * (1 - spread), 2)
                    high = round(price * (1 + spread), 2)
                    return f"${low:.2f} – ${high:.2f}" if low != high else f"${low:.2f}"

                plays_for_this = []

                # Pullback / Support Play
                if support or current_price:
                    entry_p = support or (current_price * 0.97 if current_price else 0)
                    stop_p = support * 0.93 if support and support > 0 else (entry_p * 0.90 if entry_p > 0 else 0)
                    tgt_p = resistance or (current_price * 1.12 if current_price else entry_p * 1.15)
                    if direction == "Long" and tgt_p and entry_p and tgt_p < entry_p:
                        tgt_p = entry_p * 1.18
                    plays_for_this.append({
                        "Ticker": ticker, "Scenario": f"{scenario_base} — Pullback/Support Play",
                        "Direction": direction, "Play Status": base_status,
                        "Entry": make_zone(entry_p), "Stop_Loss": f"${stop_p:.2f}" if stop_p > 0 else "TBD",
                        "Targets": make_zone(tgt_p), "Prob T1": prob_t1, "Prob T2": prob_t2,
                        "Blog Link": link, "Pub Date": pub_date.strftime("%Y-%m-%d"), "Days Old": days_old
                    })

                # Breakout / Expansion Play
                if current_price or resistance:
                    entry_p2 = resistance or (current_price * 1.03 if current_price else 0)
                    stop_p2 = (current_price * 0.97 if current_price else entry_p2 * 0.95) if direction == "Long" else (entry_p2 * 1.04)
                    tgt_p2 = (resistance * 1.15 if resistance else (current_price * 1.22 if current_price else 0)) if direction == "Long" else (current_price * 0.88 if current_price else 0)
                    if direction == "Long" and tgt_p2 and entry_p2 and tgt_p2 < entry_p2 * 1.08:
                        tgt_p2 = entry_p2 * 1.20
                    plays_for_this.append({
                        "Ticker": ticker, "Scenario": f"{scenario_base} — Breakout/Expansion Play",
                        "Direction": direction, "Play Status": base_status.replace("IN ENTRY ZONE", "⏳ Monitoring Breakout"),
                        "Entry": make_zone(entry_p2), "Stop_Loss": f"${stop_p2:.2f}" if stop_p2 > 0 else "TBD",
                        "Targets": make_zone(tgt_p2), "Prob T1": prob_t1, "Prob T2": prob_t2,
                        "Blog Link": link, "Pub Date": pub_date.strftime("%Y-%m-%d"), "Days Old": days_old
                    })

                # CHANGED: Appends all plays parsed without any limiters or slicing
                all_plays.extend(plays_for_this)  

            except Exception:
                continue

        if not all_plays:
            st.warning("No plays found in the lookback window. Showing fallback.")
            return get_fallback_playbook()

        all_plays.sort(key=lambda x: (-x.get("Days Old", 99), x["Ticker"]))
        return all_plays

    except Exception as e:
        st.warning(f"Blog sync issue: {str(e)[:150]}. Showing fallback data.")
        return get_fallback_playbook()


# OPTIMIZATION: Updated down-script to safely handle large batches of tickers
def enrich_with_live_prices(df):
    tickers = df['Ticker'].unique().tolist()
    live_prices = {}
    if tickers:
        try:
            # Using period="5d" instead of 1d/1m downscaling to ensure yfinance has cached closing quotes 
            # for a large block query without parsing heavy microsecond chunks.
            data = yf.download(" ".join(tickers), period="5d", group_by='ticker', progress=False, auto_adjust=True)
            for t in tickers:
                try:
                    if len(tickers) > 1:
                        live_prices[t] = round(float(data[t]['Close'].iloc[-1]), 2)
                    else:
                        live_prices[t] = round(float(data['Close'].iloc[-1]), 2)
                except:
                    live_prices[t] = None
        except:
            pass
    df['Live Price'] = df['Ticker'].map(live_prices)
    return df
