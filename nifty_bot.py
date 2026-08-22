import os
import json
import requests
import yfinance as.NS", "ICICIBANK.NS",
 yf
import pandas as pd
import feedparser
from datetime import datetime
import pytz
import base64
import re

# --- CONFIGURATION ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
REPO_OWNER = "duttas-clinic"
REPO_NAME = "mybotiphon"

# Risk Management Settings
RISK_PER_TRADE = 1000  # Risk ₹1,000 per trade (Adjust this to your capital)

IST = pytz.timezone('Asia/Kolkata')
NOW_IST = datetime.now(IST)
DATE_STR = NOW_IST.strftime("%Y-%m-%d")
TIME_STR = NOW_IST.strftime("%H:%M:%S IST")

NIFTY_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SB    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NSIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "BA", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "LT.NSJFINANCE.NS",
    "LT.NS", "ITC.NS", "AXISBANK", "ITC.NS", "AXISBANK.NS", "ASIANPAINT.NS", ".NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "MA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPROULTRACEMCO.NS", "WIPRO.NS", "ONGC.NS",
    ".NS", "ONGC.NS",
    "NTPC.NS", "M&M.NS",NTPC.NS", "M&M.NS", "TATAMOTORS.NS", "HCL "TATAMOTORS.NS", "HCLTECH.NS", "POWERGRID.NS",
TECH.NS", "POWERGRID.NS",
    "JSWSTEEL.NS", "TATA    "JSWSTEEL.NS", "TATASTEEL.NS", "BAJAJFINSVSTEEL.NS", "BAJAJFINSV.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "DRREDDY.NS", "CIPLA.NS", ".NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "TECHM.NSDIVISLAB.NS", "TECHM.NS", "GRASIM.NS",
    "EIC", "GRASIM.NS",
    "EICHERMOT.NS", "COALINDIA.NHERMOT.NS", "COALINDIA.NS", "BPCL.NS", "BRITANNS", "BPCL.NS", "BRITANNIA.NS", "HEROMOTOCO.NS",IA.NS", "HEROMOTOCO.NS",
    "SBILIFE.NS", "INDUS
    "SBILIFE.NS", "INDUSINDBK.NS", "HINDALCO.NINDBK.NS", "HINDALCO.NS", "UPL.NS", "NESTLES", "UPL.NS", "NESTLEIND.NS",
    "APOLLOHOSPIND.NS",
    "APOLLOHOSP.NS", "TATACONSUM.NS",.NS", "TATACONSUM.NS", "BAJAJ-AUTO.NS", "LTIM "BAJAJ-AUTO.NS", "LTIM.NS", "DLF.NS"
]

.NS", "DLF.NS"
]

# --- GITHUB & TELEGRAM FUNCTIONS ---
def send# --- GITHUB & TELEGRAM FUNCTIONS ---
def send_telegram(msg):
    url = f"https://api_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
   .telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TG_CHAT_ID requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown, "text": msg, "parse_mode": "Markdown"})

def get_github_file(filename):
    url"})

def get_github_file(filename):
    url = f"https://api.github.com/repos/{REPO_OWNER = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"
    headers}/{REPO_NAME}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN} = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers)."}
    res = requests.get(url, headers=headers).json()
    if 'content' in res:
json()
    if 'content' in res:
        return json.loads(base64.b64decode(res        return json.loads(base64.b64decode(res['content']).decode('utf-8')), res['sha['content']).decode('utf-8')), res['sha']
    return [], None

def update_github_file']
    return [], None

def update_github_file(filename, data, sha):
    url = f"https(filename, data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"
    headers = {"Authorization_NAME}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
   ": f"token {GITHUB_TOKEN}"}
    content = base64.b64encode(json.dumps(data content = base64.b64encode(json.dumps(data, indent=2).encode('utf-8')).decode, indent=2).encode('utf-8')).decode('utf-8')
    payload = {"message":('utf-8')
    payload = {"message": f"Update {filename} at {TIME_STR}", " f"Update {filename} at {TIME_STR}", "content": content, "sha": sha}
    requestscontent": content, "sha": sha}
    requests.put(url, headers=headers, json=payload)

#.put(url, headers=headers, json=payload)

# --- TECHNICAL CALCULATIONS ---
def calculate_rsi --- TECHNICAL CALCULATIONS ---
def calculate_rsi(series, period=14):
    delta = series(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > .diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
   =1/period, adjust=False).mean()
    rs = gain / loss
    return 100 rs = gain / loss
    return 100 - (100 / (1 + rs))

 - (100 / (1 + rs))

def fetch_news_for_stock(ticker_name):
    trydef fetch_news_for_stock(ticker_name):
    try:
        feed = feedparser.parse("https://www:
        feed = feedparser.parse("https://www.moneycontrol.com/rss/business.xml")
        headlines = [.moneycontrol.com/rss/business.xml")
        headlines = [entry.get('title', '') for entry in feed.entries[:entry.get('title', '') for entry in feed.entries[:15]]
        return " | ".join(headlines15]]
        return " | ".join(headlines)
    except:
        return "No news data)
    except:
        return "No news data available."

def ai_verify_green_flag(ticker, setup available."

def ai_verify_green_flag(ticker, setup_data, news_headlines):
    prompt = f"""_data, news_headlines):
    prompt = f"""You are a strict financial analyst. 
Technical Setup for {You are a strict financial analyst. 
Technical Setup for {ticker}: Price ₹{setup_data['price']}, Rticker}: Price ₹{setup_data['price']}, RSI {setup_data['rsi']}, Volume {setupSI {setup_data['rsi']}, Volume {setup_data['vol_mult']}x average.
Recent Market News_data['vol_mult']}x average.
Recent Market News: {news_headlines}
RULE: Only approve if: {news_headlines}
RULE: Only approve if there is stock-specific positive news OR if the general market news there is stock-specific positive news OR if the general market news is highly bullish. Reject if news is negative or unrelated. is highly bullish. Reject if news is negative or unrelated.
Reply ONLY with JSON: {{"green_flag": true
Reply ONLY with JSON: {{"green_flag": true/false, "reasoning": "..."}}"""
   /false, "reasoning": "..."}}"""
    headers = {"Authorization": f"Bearer {AI_API_KEY headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    data}", "Content-Type": "application/json"}
    data = {"model": "openrouter/free", "messages": = {"model": "openrouter/free", "messages": [{"role": "user", "content": prompt}]} [{"role": "user", "content": prompt}]}
    try:
        res = requests.post("https
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions",://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
 headers=headers, json=data, timeout=30)
        content = res.json()['choices'][0]['message']['        content = res.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        return\}', content, re.DOTALL)
        return json.loads(match.group(0)) if match else {"green json.loads(match.group(0)) if match else {"green_flag": False, "reasoning": "AI format error_flag": False, "reasoning": "AI format error"}
    except:
        return {"green_flag":"}
    except:
        return {"green_flag": False, "reasoning": "AI API Error"}

 False, "reasoning": "AI API Error"}

# --- MODE 1: 8:30 AM# --- MODE 1: 8:30 AM PRE-MARKET SCREENER ---
def run_pre PRE-MARKET SCREENER ---
def run_pre_market_screener():
    print(f"Running Pre_market_screener():
    print(f"Running Pre-Market Screener at {TIME_STR}...")
-Market Screener at {TIME_STR}...")
    print("Downloading 1 year of market    print("Downloading 1 year of market data for 50 stocks...")
    data = data for 50 stocks...")
    data = yf.download(NIFTY_STOCKS, period="1 yf.download(NIFTY_STOCKS, period="1y", group_by='ticker', threads=5)
y", group_by='ticker', threads=5)
    
    setups = []
    total_scanned =     
    setups = []
    total_scanned = 0
    failed_trend = 0
    failed0
    failed_trend = 0
    failed_rsi = 0
    failed_volume = 0_rsi = 0
    failed_volume = 0
    failed_data = 0
    
    for ticker in
    failed_data = 0
    
    for ticker in NIFTY_STOCKS:
        try:
            NIFTY_STOCKS:
        try:
            df = data[ticker].dropna()
            if df = data[ticker].dropna()
            if len(df) < 200: 
                failed len(df) < 200: 
                failed_data += 1
                continue
            
            total_scanned_data += 1
                continue
            
            total_scanned += 1
            close, volume = df['Close += 1
            close, volume = df['Close'], df['Volume']
            df['EMA50'], df['Volume']
            df['EMA50'] = close.ewm(span=50, adjust'] = close.ewm(span=50, adjust=False).mean()
            df['EMA200=False).mean()
            df['EMA200'] = close.ewm(span=200,'] = close.ewm(span=200, adjust=False).mean()
            df['RSI'] adjust=False).mean()
            df['RSI'] = calculate_rsi(close)
            df['Vol_MA = calculate_rsi(close)
            df['Vol_MA20'] = volume.rolling(20).mean20'] = volume.rolling(20).mean()
            
            latest = df.iloc[-1]
()
            
            latest = df.iloc[-1]
            price, ema50, ema200 =            price, ema50, ema200 = latest['Close'], latest['EMA50'], latest[' latest['Close'], latest['EMA50'], latest['EMA200']
            rsi, vol,EMA200']
            rsi, vol, vol_ma = latest['RSI'], latest['Volume'], vol_ma = latest['RSI'], latest['Volume'], latest['Vol_MA20']
            
            if not latest['Vol_MA20']
            
            if not (price > ema50 > ema200): (price > ema50 > ema200): 
                failed_trend += 1
                continue
 
                failed_trend += 1
                continue
            if not (45 <= rsi <= 6            if not (45 <= rsi <= 65): 
                failed_rsi += 1
               5): 
                failed_rsi += 1
                continue
            if vol <= (1.5 * vol continue
            if vol <= (1.5 * vol_ma): 
                failed_volume += 1
                continue_ma): 
                failed_volume += 1
                continue
            
            atr = (df['High'] - df['
            
            atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1Low']).rolling(14).mean().iloc[-1]
            sl_price = price - (1.5]
            sl_price = price - (1.5 * atr)
            risk = price - sl_price
 * atr)
            risk = price - sl_price
            tp_price = price + (2.5 * risk            tp_price = price + (2.5 * risk)
            
            setups.append({
                "ticker":)
            
            setups.append({
                "ticker": ticker, "clean_ticker": ticker.replace(".NS", ticker, "clean_ticker": ticker.replace(".NS", ""),
                "price": round(price, 2), ""),
                "price": round(price, 2), "rsi": round(rsi, 2),
 "rsi": round(rsi, 2),
                "sl": round(sl_price, 2), "                "sl": round(sl_price, 2), "tp": round(tp_price, 2),
                "tp": round(tp_price, 2),
                "vol_mult": round(vol / vol_ma, 2),vol_mult": round(vol / vol_ma, 2), "atr": round(atr, 2)
            "atr": round(atr, 2)
            })
        except Exception as e:
            failed_data })
        except Exception as e:
            failed_data += 1
            continue

    print(f"DEBUG += 1
            continue

    print(f"DEBUG: Scanned={total_scanned}, TrendFail={failed: Scanned={total_scanned}, TrendFail={failed_trend}, RSIFail={failed_rsi}, Vol_trend}, RSIFail={failed_rsi}, VolFail={failed_volume}, DataFail={failed_data}")

Fail={failed_volume}, DataFail={failed_data}")

    setups.sort(key=lambda x: x['vol_mult'],    setups.sort(key=lambda x: x['vol_mult'], reverse=True)
    top_3 = setups[:3 reverse=True)
    top_3 = setups[:3]
    
    _, sha = get_github_file("]
    
    _, sha = get_github_file("daily_watchlist.json")
    update_github_file("daily_watchlist.json")
    update_github_file("daily_watchlist.json", top_3, sha)
daily_watchlist.json", top_3, sha)
    
    if top_3:
        msg = f    
    if top_3:
        msg = f"🇮🇳 *Nifty Pre-M"🇮🇳 *Nifty Pre-Market Watchlist*\n📅 {DATE_STR}arket Watchlist*\n📅 {DATE_STR} {TIME_STR}\n\n"
        for i {TIME_STR}\n\n"
        for i, s in enumerate(top_3, 1):
, s in enumerate(top_3, 1):
            # Calculate Quantity based on fixed risk
            # Calculate Quantity based on fixed risk
            risk_per_share = s['price'] -            risk_per_share = s['price'] - s['sl']
            qty = int(R s['sl']
            qty = int(RISK_PER_TRADE / risk_per_share) if risk_perISK_PER_TRADE / risk_per_share) if risk_per_share > 0 else 1
            if qty_share > 0 else 1
            if qty == 0: qty = 1
            
            msg == 0: qty = 1
            
            msg += (f"*{i}. {s['clean_t += (f"*{i}. {s['clean_ticker']}*\n"
                    f"icker']}*\n"
                    f" *Entry Price:* ₹{s['price']} | *Entry Price:* ₹{s['price']} | *LTP:* ₹{s['price']}\n *LTP:* ₹{s['price']}\n"
                    f"📦 *Qty:* {"
                    f"📦 *Qty:* {qty} (Risk: ₹{RISK_PER_TRAqty} (Risk: ₹{RISK_PER_TRADE})\n"
                    f"🛑DE})\n"
                    f"🛑 *SL:* ₹{s['sl']} | *T *SL:* ₹{s['sl']} | *TSL:* ₹{s['sl']}\n"
SL:* ₹{s['sl']}\n"
                    f"🎯 *TP:* ₹{s                    f"🎯 *TP:* ₹{s['tp']}\n"
                    f"['tp']}\n"
                    f" RSI: {s['rsi']} RSI: {s['rsi']} | Vol: {s['vol_mult']}x\n\n | Vol: {s['vol_mult']}x\n\n")
        msg += "⏳")
        msg += "⏳ _Scanning for 9:30 AM Green Flag _Scanning for 9:30 AM Green Flag confirmation..._"
    else:
        msg = ( confirmation..._"
    else:
        msg = (f"🇮🇳 *Nifty Pref"🇮🇳 *Nifty Pre-Market Watchlist*\n📅 {DATE_STR-Market Watchlist*\n📅 {DATE_STR} {TIME_STR}\n\n"
               f"} {TIME_STR}\n\n"
               f"❌ *No stocks met criteria.*\n\n"❌ *No stocks met criteria.*\n\n"
               f"📊 *Screening Summary (
               f"📊 *Screening Summary (Scanned: {total_scanned}):*\n"
Scanned: {total_scanned}):*\n"
               f"📉 Failed Trend: *{failed               f"📉 Failed Trend: *{failed_trend}*\n"
               f"_trend}*\n"
               f"⚖️ Failed Momentum: *{failed_rsi⚖️ Failed Momentum: *{failed_rsi}*\n"
               f"📉 Failed}*\n"
               f"📉 Failed Volume: *{failed_volume}*\n"
               Volume: *{failed_volume}*\n"
               f"⚠️ Data Errors: *{failed f"⚠️ Data Errors: *{failed_data}*\n\n"
               f"_data}*\n\n"
               f"🛡️ _Capital preserved! Market🛡️ _Capital preserved! Market conditions do not favor swing entries today._")
               
    conditions do not favor swing entries today._")
               
    send_telegram(msg)
    print("Screener send_telegram(msg)
    print("Screener complete.")

# --- MODE 2: 9: complete.")

# --- MODE 2: 9:30 AM GREEN FLAG SCAN ---
def run_green_flag30 AM GREEN FLAG SCAN ---
def run_green_flag_scan():
    print(f"Running 9:3_scan():
    print(f"Running 9:30 AM Green Flag Scan...")
    watchlist,0 AM Green Flag Scan...")
    watchlist, _ = get_github_file("daily_watchlist.json") _ = get_github_file("daily_watchlist.json")
    
    if not watchlist:
        send_tele
    
    if not watchlist:
        send_telegram(f"⚠️ *9:30gram(f"⚠️ *9:30 AM Update*\nNo pre-market watchlist found for today AM Update*\nNo pre-market watchlist found for today.")
        return

    confirmed_trades = []
.")
        return

    confirmed_trades = []
    active_trades, sha_active = get_github_file    active_trades, sha_active = get_github_file("active_trades.json")
    history, sha_history("active_trades.json")
    history, sha_history = get_github_file("trade_history.json")
    = get_github_file("trade_history.json")
    news_headlines = fetch_news_for_stock("Nifty") news_headlines = fetch_news_for_stock("Nifty")

    msg = f"🚦 *9:

    msg = f"🚦 *9:30 AM Green Flag Report*\n📅 {30 AM Green Flag Report*\n📅 {DATE_STR} {TIME_STR}\n\n"
    
DATE_STR} {TIME_STR}\n\n"
    
    for setup in watchlist:
        ticker = setup    for setup in watchlist:
        ticker = setup['ticker']
        try:
            live_data =['ticker']
        try:
            live_data = yf.download(ticker, period='2d', interval yf.download(ticker, period='2d', interval='5m')
            if len(live_data)='5m')
            if len(live_data) < 3: continue
            
            early_vol = live_data < 3: continue
            
            early_vol = live_data['Volume'].iloc[:3].sum()
            avg['Volume'].iloc[:3].sum()
            avg_5m_vol = live_data['Volume'].rolling(_5m_vol = live_data['Volume'].rolling(20).mean().iloc[-1]
            current20).mean().iloc[-1]
            current_price = live_data['Close'].iloc[-1]
_price = live_data['Close'].iloc[-1]
            
            ai_result = ai_verify_green_flag(setup['            
            ai_result = ai_verify_green_flag(setup['clean_ticker'], setup, news_headlines)
            
clean_ticker'], setup, news_headlines)
            
            if early_vol > (1.2 * avg_            if early_vol > (1.2 * avg_5m_vol) and current_price >= setup['price']5m_vol) and current_price >= setup['price'] and ai_result.get('green_flag'):
                risk and ai_result.get('green_flag'):
                risk_per_share = setup['price'] - setup['sl']_per_share = setup['price'] - setup['sl']
                qty = int(RISK_PER_TRADE / risk
                qty = int(RISK_PER_TRADE / risk_per_share) if risk_per_share > 0 else _per_share) if risk_per_share > 0 else 1
                if qty == 0: qty1
                if qty == 0: qty = 1
                
                trade_record = {
                    " = 1
                
                trade_record = {
                    "id": len(history) + 1, "ticker":id": len(history) + 1, "ticker": setup['clean_ticker'],
                    "entry_time": setup['clean_ticker'],
                    "entry_time": f"{DATE_STR} {TIME_STR}", "entry_price f"{DATE_STR} {TIME_STR}", "entry_price": setup['price'],
                    "qty": qty,": setup['price'],
                    "qty": qty, "sl": setup['sl'], "tp": setup[' "sl": setup['sl'], "tp": setup['tp'],
                    "atr": setup['atr'], "tp'],
                    "atr": setup['atr'], "status": "OPEN", "tsl": setup['slstatus": "OPEN", "tsl": setup['sl'],
                    "ai_reasoning": ai_result.get(''],
                    "ai_reasoning": ai_result.get('reasoning', '')
                }
                
                active_trreasoning', '')
                }
                
                active_trades.append(trade_record)
                history.append(tradeades.append(trade_record)
                history.append(trade_record)
                confirmed_trades.append(setup['clean_record)
                confirmed_trades.append(setup['clean_ticker'])
                
                msg += (f"✅_ticker'])
                
                msg += (f"✅ *{setup['clean_ticker']} CONFIRMED*\ *{setup['clean_ticker']} CONFIRMED*\n"
                        f"🎯 Entry:n"
                        f"🎯 Entry: ₹{setup['price']} | LTP: ₹{ ₹{setup['price']} | LTP: ₹{current_price}\n"
                        f"current_price}\n"
                        f" Qty: {qty} (Risk: ₹{ Qty: {qty} (Risk: ₹{RISK_PER_TRADE})\n"
                        fRISK_PER_TRADE})\n"
                        f"🛑 SL: ₹{setup['sl']}"🛑 SL: ₹{setup['sl']} | TSL: ₹{setup['sl']}\n | TSL: ₹{setup['sl']}\n"
                        f"🎯 TP: ₹{"
                        f"🎯 TP: ₹{setup['tp']}\n"
                        f"setup['tp']}\n"
                        f" AI: {ai_result.get('reasoning', AI: {ai_result.get('reasoning', '')}\n\n")
            else:
                msg '')}\n\n")
            else:
                msg += f"❌ *{setup['clean_ticker += f"❌ *{setup['clean_ticker']} REJECTED*\n   Reason: Volume/Price/A']} REJECTED*\n   Reason: Volume/Price/AI failed.\n\n"
        except Exception as eI failed.\n\n"
        except Exception as e:
            msg += f"⚠️ *:
            msg += f"⚠️ *{setup['clean_ticker']} ERROR*\n   {{setup['clean_ticker']} ERROR*\n   {str(e)[:50]}\n\n"

   str(e)[:50]}\n\n"

    if not confirmed_trades:
        msg += " if not confirmed_trades:
        msg += "️ _No Green Flags confirmed. Staying in️ _No Green Flags confirmed. Staying in cash._"
        
    send_telegram(msg)
 cash._"
        
    send_telegram(msg)
    update_github_file("active_trades.json", active    update_github_file("active_trades.json", active_trades, sha_active)
    update_github_file_trades, sha_active)
    update_github_file("trade_history.json", history, sha_history)

#("trade_history.json", history, sha_history)

# --- MAIN ROUTER ---
def main():
    hour --- MAIN ROUTER ---
def main():
    hour = NOW_IST.hour
    if 8 <= hour = NOW_IST.hour
    if 8 <= hour < 9: 
        run_pre_market_screener < 9: 
        run_pre_market_screener()
    elif 9 <= hour < 10()
    elif 9 <= hour < 10: 
        run_green_flag_scan()
    else:: 
        run_green_flag_scan()
    else:
        print("Running outside scheduled hours. Defaulting to
        print("Running outside scheduled hours. Defaulting to screener.")
        run_pre_market_screener() screener.")
        run_pre_market_screener()

if __name__ == "__main__":


if __name__ == "__main__":
    main()
