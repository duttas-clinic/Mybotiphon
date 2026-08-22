import os
import json
import requests
import yfinance as yf
import pandas as pd
import feedparser
from datetime import datetime
import pytz
import base64

# --- CONFIGURATION ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
REPO_OWNER = "duttas-clinic"
REPO_NAME = "mybotiphon"

IST = pytz.timezone('Asia/Kolkata')
NOW_IST = datetime.now(IST)
DATE_STR = NOW_IST.strftime("%Y-%m-%d")
TIME_STR = NOW_IST.strftime("%H:%M:%S IST")

NIFTY_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "LT.NS", "ITC.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS", "ONGC.NS",
    "NTPC.NS", "M&M.NS", "TATAMOTORS.NS", "HCLTECH.NS", "POWERGRID.NS",
    "JSWSTEEL.NS", "TATASTEEL.NS", "BAJAJFINSV.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "TECHM.NS", "GRASIM.NS",
    "EICHERMOT.NS", "COALINDIA.NS", "BPCL.NS", "BRITANNIA.NS", "HEROMOTOCO.NS",
    "SBILIFE.NS", "INDUSINDBK.NS", "HINDALCO.NS", "UPL.NS", "NESTLEIND.NS",
    "APOLLOHOSP.NS", "TATACONSUM.NS", "BAJAJ-AUTO.NS", "LTIM.NS", "DLF.NS"
]

# --- GITHUB & TELEGRAM FUNCTIONS ---
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_github_file(filename):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(url, headers=headers).json()
    if 'content' in res:
        return json.loads(base64.b64decode(res['content']).decode('utf-8')), res['sha']
    return [], None

def update_github_file(filename, data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = base64.b64encode(json.dumps(data, indent=2).encode('utf-8')).decode('utf-8')
    payload = {"message": f"Update {filename} at {TIME_STR}", "content": content, "sha": sha}
    requests.put(url, headers=headers, json=payload)

# --- TECHNICAL CALCULATIONS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_news_for_stock(ticker_name):
    """Fetches top financial news headlines"""
    try:
        # Using Moneycontrol RSS feed (Free and reliable for Indian stocks)
        feed = feedparser.parse("https://www.moneycontrol.com/rss/business.xml")
        headlines = []
        for entry in feed.entries[:15]: # Get top 15 headlines
            headlines.append(entry.get('title', ''))
        return " | ".join(headlines)
    except:
        return "No news data available."

def ai_verify_green_flag(ticker, setup_data, news_headlines):
    """Asks AI to verify if news supports the technical setup"""
    prompt = f"""You are a strict financial analyst. 
Technical Setup for {ticker}: Price ₹{setup_data['price']}, RSI {setup_data['rsi']}, Volume {setup_data['vol_mult']}x average.
Recent Market News: {news_headlines}

RULE: Only approve if there is stock-specific positive news OR if the general market news is highly bullish. Reject if news is negative or unrelated.
Reply ONLY with JSON: {{"green_flag": true/false, "reasoning": "..."}}"""

    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "openrouter/free", "messages": [{"role": "user", "content": prompt}]}
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        content = res.json()['choices'][0]['message']['content']
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        return json.loads(match.group(0)) if match else {"green_flag": False, "reasoning": "AI format error"}
    except:
        return {"green_flag": False, "reasoning": "AI API Error"}

# --- MODE 1: 8:30 AM PRE-MARKET SCREENER ---
def run_pre_market_screener():
    print(f"Running 8:30 AM Pre-Market Screener...")
    data = yf.download(NIFTY_STOCKS, period="6mo", group_by='ticker', threads=5)
    setups = []
    
    for ticker in NIFTY_STOCKS:
        try:
            df = data[ticker].dropna()
            if len(df) < 200: continue
            close, volume = df['Close'], df['Volume']
            df['EMA50'] = close.ewm(span=50, adjust=False).mean()
            df['EMA200'] = close.ewm(span=200, adjust=False).mean()
            df['RSI'] = calculate_rsi(close)
            df['Vol_MA20'] = volume.rolling(20).mean()
            
            latest = df.iloc[-1]
            price, ema50, ema200 = latest['Close'], latest['EMA50'], latest['EMA200']
            rsi, vol, vol_ma = latest['RSI'], latest['Volume'], latest['Vol_MA20']
            
            if not (price > ema50 > ema200): continue
            if not (45 <= rsi <= 65): continue
            if vol <= (1.5 * vol_ma): continue
            
            atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
            sl_price = price - (1.5 * atr)
            risk = price - sl_price
            tp_price = price + (2.5 * risk)
            
            setups.append({
                "ticker": ticker, "clean_ticker": ticker.replace(".NS", ""),
                "price": round(price, 2), "rsi": round(rsi, 2),
                "sl": round(sl_price, 2), "tp": round(tp_price, 2),
                "vol_mult": round(vol / vol_ma, 2), "atr": round(atr, 2)
            })
        except: continue

    setups.sort(key=lambda x: x['vol_mult'], reverse=True)
    top_3 = setups[:3]
    
    # Save to GitHub for the 9:30 AM run to read
    _, sha = get_github_file("daily_watchlist.json")
    update_github_file("daily_watchlist.json", top_3, sha)
    
    # Send Telegram
    if top_3:
        msg = f"🇮🇳 *Nifty Pre-Market Watchlist*\n📅 {DATE_STR} {TIME_STR}\n\n"
        for i, s in enumerate(top_3, 1):
            msg += (f"*{i}. {s['clean_ticker']}* @ ₹{s['price']}\n"
                    f"   RSI: {s['rsi']} | Vol: {s['vol_mult']}x\n"
                    f"   SL: ₹{s['sl']} | TP: ₹{s['tp']}\n\n")
        msg += "⏳ _Scanning for 9:30 AM Green Flag confirmation..._"
    else:
        msg = f"🇮🇳 *Nifty Pre-Market Watchlist*\n📅 {DATE_STR} {TIME_STR}\n\nNo stocks met criteria. Capital preserved! 🛡️"
    send_telegram(msg)

# --- MODE 2: 9:30 AM GREEN FLAG SCAN ---
def run_green_flag_scan():
    print(f"Running 9:30 AM Green Flag Scan...")
    watchlist, _ = get_github_file("daily_watchlist.json")
    
    if not watchlist:
        send_telegram(f"⚠️ *9:30 AM Update*\nNo pre-market watchlist found for today.")
        return

    confirmed_trades = []
    active_trades, sha_active = get_github_file("active_trades.json")
    history, sha_history = get_github_file("trade_history.json")
    news_headlines = fetch_news_for_stock("Nifty") # General market news

    msg = f" *9:30 AM Green Flag Report*\n📅 {DATE_STR} {TIME_STR}\n\n"
    
    for setup in watchlist:
        ticker = setup['ticker']
        try:
            # Fetch live 5-minute data for the first 15 mins of market
            live_data = yf.download(ticker, period='2d', interval='5m')
            if len(live_data) < 3: continue
            
            # Check Volume Ignition (First 3 candles = 9:15 to 9:30)
            early_vol = live_data['Volume'].iloc[:3].sum()
            avg_5m_vol = live_data['Volume'].rolling(20).mean().iloc[-1]
            
            # Check Price Holding (Current price > yesterday's high or setup price)
            current_price = live_data['Close'].iloc[-1]
            
            # AI Verification
            ai_result = ai_verify_green_flag(setup['clean_ticker'], setup, news_headlines)
            
            if early_vol > (1.2 * avg_5m_vol) and current_price >= setup['price'] and ai_result.get('green_flag'):
                # GREEN FLAG CONFIRMED!
                qty = int(5000 / (setup['price'] - setup['sl'])) # Risk ₹5000 per trade (adjust as needed)
                
                trade_record = {
                    "id": len(history) + 1, "ticker": setup['clean_ticker'],
                    "entry_time": f"{DATE_STR} {TIME_STR}", "entry_price": setup['price'],
                    "qty": qty, "sl": setup['sl'], "tp": setup['tp'],
                    "atr": setup['atr'], "status": "OPEN", "tsl": setup['sl'],
                    "ai_reasoning": ai_result.get('reasoning', '')
                }
                
                active_trades.append(trade_record)
                history.append(trade_record)
                confirmed_trades.append(setup['clean_ticker'])
                
                msg += (f"✅ *{setup['clean_ticker']} CONFIRMED*\n"
                        f"   Entry: ₹{setup['price']} | Qty: {qty}\n"
                        f"   SL: ₹{setup['sl']} | TP: ₹{setup['tp']}\n"
                        f"   🤖 AI: {ai_result.get('reasoning', '')}\n\n")
            else:
                msg += f"❌ *{setup['clean_ticker']} REJECTED*\n   Reason: Volume/Price/AI failed.\n\n"
        except Exception as e:
            msg += f"⚠️ *{setup['clean_ticker']} ERROR*\n   {str(e)[:50]}\n\n"

    if not confirmed_trades:
        msg += "🛡️ _No Green Flags confirmed. Staying in cash._"
        
    send_telegram(msg)
    
    # Save updated ledgers
    update_github_file("active_trades.json", active_trades, sha_active)
    update_github_file("trade_history.json", history, sha_history)

# --- MAIN ROUTER ---
def main():
    # Determine mode based on current IST time
    hour = NOW_IST.hour
    if 8 <= hour < 9: # 8:30 AM run
        run_pre_market_screener()
    elif 9 <= hour < 10: # 9:30 AM run
        run_green_flag_scan()
    else:
        print("Running outside scheduled hours. Defaulting to screener.")
        run_pre_market_screener()

if __name__ == "__main__":
    main()
