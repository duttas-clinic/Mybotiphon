import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import base64

# --- CONFIGURATION ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "duttas-clinic"
REPO_NAME = "mybotiphon"

IST = pytz.timezone('Asia/Kolkata')
NOW_IST = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

# Top 50 High-Liquidity Nifty Stocks (Phase 1 Optimization)
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
    payload = {"message": f"Update {filename} at {NOW_IST}", "content": content, "sha": sha}
    requests.put(url, headers=headers, json=payload)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_screener():
    print(f"Starting Nifty Screener at {NOW_IST}...")
    
    # Batch download 6 months of data for all 50 stocks at once
    print("Downloading market data...")
    data = yf.download(NIFTY_STOCKS, period="6mo", group_by='ticker', threads=5)
    
    setups = []
    
    for ticker in NIFTY_STOCKS:
        try:
            df = data[ticker].dropna()
            if len(df) < 200: continue
            
            close = df['Close']
            volume = df['Volume']
            
            # Calculate Indicators
            df['EMA50'] = close.ewm(span=50, adjust=False).mean()
            df['EMA200'] = close.ewm(span=200, adjust=False).mean()
            df['RSI'] = calculate_rsi(close)
            df['Vol_MA20'] = volume.rolling(20).mean()
            
            latest = df.iloc[-1]
            
            price = latest['Close']
            ema50 = latest['EMA50']
            ema200 = latest['EMA200']
            rsi = latest['RSI']
            vol = latest['Volume']
            vol_ma = latest['Vol_MA20']
            
            # --- THE RULEBOOK ---
            # 1. Trend Alignment
            if not (price > ema50 > ema200): continue
            
            # 2. Momentum (RSI 45-65)
            if not (45 <= rsi <= 65): continue
            
            # 3. Volume Breakout (> 1.5x average)
            if vol <= (1.5 * vol_ma): continue
            
            # Calculate Setup Metrics
            atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
            sl_price = price - (1.5 * atr)
            risk = price - sl_price
            tp_price = price + (2.5 * risk)
            
            setups.append({
                "ticker": ticker.replace(".NS", ""),
                "price": round(price, 2),
                "rsi": round(rsi, 2),
                "sl": round(sl_price, 2),
                "tp": round(tp_price, 2),
                "vol_mult": round(vol / vol_ma, 2)
            })
        except Exception as e:
            continue

    # Sort by highest volume multiplier (strongest breakouts first)
    setups.sort(key=lambda x: x['vol_mult'], reverse=True)
    top_3 = setups[:3]
    
    # Format Telegram Message
    if top_3:
        msg = f"🇳 *Nifty Pre-Market Watchlist*\n📅 {NOW_IST}\n\n"
        for i, s in enumerate(top_3, 1):
            msg += (f"*{i}. {s['ticker']}* @ ₹{s['price']}\n"
                    f"   RSI: {s['rsi']} | Vol: {s['vol_mult']}x\n"
                    f"   SL: ₹{s['sl']} | TP: ₹{s['tp']}\n\n")
        msg += "⚠️ _Wait for 9:30 AM Green Flag confirmation before entering._"
    else:
        msg = f"🇳 *Nifty Pre-Market Watchlist*\n📅 {NOW_IST}\n\nNo stocks met the strict Rulebook criteria today. Capital preserved! 🛡️"
        
    send_telegram(msg)
    print("Screener complete.")

if __name__ == "__main__":
    run_screener()
