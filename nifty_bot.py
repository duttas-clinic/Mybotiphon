import os
import json
import requests
import yfinance as yf
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

RISK_PER_TRADE = 1000
BREAKOUT_BUFFER = 0.002

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

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_news_for_stock(ticker_name):
    try:
        feed = feedparser.parse("https://www.moneycontrol.com/rss/business.xml")
        headlines = [entry.get('title', '') for entry in feed.entries[:15]]
        return " | ".join(headlines)
    except:
        return "No news data available."

def ai_verify_green_flag(ticker, setup_data, news_headlines):
    prompt = f"""You are a strict financial analyst. 
Technical Setup for {ticker}: Trigger Price ₹{setup_data['trigger_entry']}, RSI {setup_data['rsi']}, Volume {setup_data['vol_mult']}x average.
Recent Market News: {news_headlines}
RULE: Only approve if there is stock-specific positive news OR if the general market news is highly bullish. Reject if news is negative or unrelated.
Reply ONLY with JSON: {{"green_flag": true/false, "reasoning": "..."}}"""
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "openrouter/free", "messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        content = res.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        return json.loads(match.group(0)) if match else {"green_flag": False, "reasoning": "AI format error"}
    except:
        return {"green_flag": False, "reasoning": "AI API Error"}

def run_pre_market_screener():
    print(f"Running Pre-Market Screener at {TIME_STR}...")
    data = yf.download(NIFTY_STOCKS, period="1y", group_by='ticker', threads=5)
    
    setups = []
    total_scanned, failed_trend, failed_rsi, failed_volume, failed_data = 0, 0, 0, 0, 0
    
    for ticker in NIFTY_STOCKS:
        try:
            df = data[ticker].dropna()
            if len(df) < 200: 
                failed_data += 1
                continue
            total_scanned += 1
            close, volume = df['Close'], df['Volume']
            df['EMA50'] = close.ewm(span=50, adjust=False).mean()
            df['EMA200'] = close.ewm(span=200, adjust=False).mean()
            df['RSI'] = calculate_rsi(close)
            df['Vol_MA20'] = volume.rolling(20).mean()
            
            latest = df.iloc[-1]
            prev_high = df['High'].iloc[-1]
            prev_low = df['Low'].iloc[-1]
            
            price, ema50, ema200 = latest['Close'], latest['EMA50'], latest['EMA200']
            rsi, vol, vol_ma = latest['RSI'], latest['Volume'], latest['Vol_MA20']
            
            if not (price > ema50 > ema200): 
                failed_trend += 1
                continue
            if not (45 <= rsi <= 65): 
                failed_rsi += 1
                continue
            if vol <= (1.5 * vol_ma): 
                failed_volume += 1
                continue
            
            trigger_entry = round(prev_high * (1 + BREAKOUT_BUFFER), 2)
            atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
            sl_price = round(min(prev_low, trigger_entry - (1.5 * atr)), 2)
            
            risk = trigger_entry - sl_price
            tp_price = round(trigger_entry + (2.5 * risk), 2)
            
            setups.append({
                "ticker": ticker, "clean_ticker": ticker.replace(".NS", ""),
                "trigger_entry": trigger_entry, "prev_close": round(price, 2),
                "rsi": round(rsi, 2), "sl": sl_price, "tp": tp_price,
                "vol_mult": round(vol / vol_ma, 2), "atr": round(atr, 2)
            })
        except: 
            failed_data += 1

    setups.sort(key=lambda x: x['vol_mult'], reverse=True)
    top_3 = setups[:3]
    
    _, sha = get_github_file("daily_watchlist.json")
    update_github_file("daily_watchlist.json", top_3, sha)
    
    if top_3:
        msg = f"🇮🇳 *Nifty Pre-Market Watchlist*\n📅 {DATE_STR} {TIME_STR}\n\n"
        for i, s in enumerate(top_3, 1):
            risk_per_share = s['trigger_entry'] - s['sl']
            qty = int(RISK_PER_TRADE / risk_per_share) if risk_per_share > 0 else 1
            if qty == 0: qty = 1
            
            msg += (f"*{i}. {s['clean_ticker']}*\n"
                    f" *Trigger Entry:* ₹{s['trigger_entry']} (Buy ONLY if it crosses this)\n"
                    f"📊 *Prev Close:* ₹{s['prev_close']} @ {DATE_STR} | *RSI:* {s['rsi']}\n"
                    f"📦 *Qty:* {qty} (Risk: ₹{RISK_PER_TRADE})\n"
                    f" *SL:* ₹{s['sl']} | *TSL:* ₹{s['sl']}\n"
                    f"🎯 *TP:* ₹{s['tp']}\n\n")
        msg += "⏳ _Scanning for 9:30 AM Green Flag confirmation..._"
    else:
        msg = (f"🇮🇳 *Nifty Pre-Market Watchlist*\n {DATE_STR} {TIME_STR}\n\n"
               f"❌ *No stocks met criteria.*\n\n"
               f"📊 *Screening Summary (Scanned: {total_scanned}):*\n"
               f"📉 Failed Trend: *{failed_trend}*\n⚖️ Failed Momentum: *{failed_rsi}*\n"
               f"📉 Failed Volume: *{failed_volume}*\n⚠️ Data Errors: *{failed_data}*\n\n"
               f"🛡️ _Capital preserved! Market conditions do not favor swing entries today._")
    send_telegram(msg)

def run_green_flag_scan():
    watchlist, _ = get_github_file("daily_watchlist.json")
    if not watchlist:
        send_telegram(f"⚠️ *9:30 AM Update*\nNo pre-market watchlist found for today.")
        return

    confirmed_trades = []
    active_trades, sha_active = get_github_file("active_trades.json")
    history, sha_history = get_github_file("trade_history.json")
    news_headlines = fetch_news_for_stock("Nifty")

    msg = f"🚦 *9:30 AM Green Flag Report*\n {DATE_STR} {TIME_STR}\n\n"
    
    for setup in watchlist:
        ticker = setup['ticker']
        try:
            live_data = yf.download(ticker, period='2d', interval='5m')
            if len(live_data) < 3: continue
            
            last_candle_time = live_data.index[-1]
            if last_candle_time.tzinfo is None:
                last_candle_time = pytz.utc.localize(last_candle_time)
            ist_time = last_candle_time.astimezone(IST).strftime('%H:%M %p IST')
            
            early_vol = live_data['Volume'].iloc[:3].sum()
            avg_5m_vol = live_data['Volume'].rolling(20).mean().iloc[-1]
            
            # THIS IS THE LINE THAT FAILED PREVIOUSLY
            current_price = live_data['Close'].iloc[-1]
            
            trigger = setup['trigger_entry']
            ai_result = ai_verify_green_flag(setup['clean_ticker'], setup, news_headlines)
            
            if early_vol > (1.2 * avg_5m_vol) and current_price >= trigger and ai_result.get('green_flag'):
                risk_per_share = trigger - setup['sl']
                qty = int(RISK_PER_TRADE / risk_per_share) if risk_per_share > 0 else 1
                if qty == 0: qty = 1
                
                trade_record = {
                    "id": len(history) + 1, "ticker": setup['clean_ticker'],
                    "entry_time": f"{DATE_STR} {TIME_STR}", "entry_price": trigger,
                    "qty": qty, "sl": setup['sl'], "tp": setup['tp'],
                    "atr": setup['atr'], "status": "OPEN", "tsl": setup['sl'],
                    "ai_reasoning": ai_result.get('reasoning', '')
                }
                active_trades.append(trade_record)
                history.append(trade_record)
                confirmed_trades.append(setup['clean_ticker'])
                msg += (f"✅ *{setup['clean_ticker']} CONFIRMED*\n"
                        f"🎯 Trigger Crossed! Entry: ₹{trigger} | LTP: ₹{current_price} @ {ist_time}\n"
                        f"📦 Qty: {qty} (Risk: ₹{RISK_PER_TRADE})\n"
                        f"🛑 SL: ₹{setup['sl']} | TSL: ₹{setup['sl']}\n"
                        f"🎯 TP: ₹{setup['tp']}\n"
                        f"🤖 AI: {ai_result.get('reasoning', '')}\n\n")
            else:
                msg += f"❌ *{setup['clean_ticker']} REJECTED*\n   Reason: Price didn't cross Trigger (₹{trigger}) or Volume/AI failed.\n\n"
        except Exception as e:
            msg += f"⚠️ *{setup['clean_ticker']} ERROR*\n   {str(e)[:50]}\n\n"

    if not confirmed_trades: 
        msg += "🛡️ _No Green Flags confirmed. Staying in cash._"
    send_telegram(msg)
    update_github_file("active_trades.json", active_trades, sha_active)
    update_github_file("trade_history.json", history, sha_history)

def run_post_market_manager():
    print(f"Running 3:45 PM Post-Market Manager...")
    active_trades, sha_active = get_github_file("active_trades.json")
    history, sha_history = get_github_file("trade_history.json")
    
    if not active_trades:
        send_telegram(f"🌙 *End of Day Report*\n📅 {DATE_STR} {TIME_STR}\n\nNo open trades. Capital is safe in cash! 💰")
        return

    msg = f"🌙 *End of Day Trade Manager*\n📅 {DATE_STR} {TIME_STR}\n\n"
    closed_today = 0
    updated_tsl = 0

    tickers_to_check = list(set([t['ticker'] + ".NS" for t in active_trades]))
    daily_data = yf.download(tickers_to_check, period='5d', group_by='ticker')
    new_active_trades = []
    
    for trade in active_trades:
        ticker_full = trade['ticker'] + ".NS"
        try:
            df = daily_data[ticker_full].dropna()
            if len(df) == 0: 
                new_active_trades.append(trade)
                continue
                
            today_date_str = df.index[-1].strftime('%d %b %Y')
            
            today_high = df['High'].iloc[-1]
            today_low = df['Low'].iloc[-1]
            today_close = df['Close'].iloc[-1]
            
            entry = trade['entry_price']
            sl = trade['sl']
            tp = trade['tp']
            qty = trade['qty']
            initial_risk = entry - sl
            
            if today_low <= sl:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = sl
                trade['exit_time'] = f"{today_date_str} 15:30 IST"
                trade['exit_reason'] = "STOP LOSS HIT"
                trade['realized_pnl'] = (sl - entry) * qty
                history.append(trade)
                closed_today += 1
                msg += f"🛑 *{trade['ticker']} STOPPED OUT*\n   Exit: ₹{sl} @ {today_date_str} | PnL: ₹{trade['realized_pnl']:.2f}\n\n"
                continue
                
            if today_high >= tp:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = tp
                trade['exit_time'] = f"{today_date_str} 15:30 IST"
                trade['exit_reason'] = "TAKE PROFIT HIT"
                trade['realized_pnl'] = (tp - entry) * qty
                history.append(trade)
                closed_today += 1
                msg += f"🎯 *{trade['ticker']} TARGET HIT!*\n   Exit: ₹{tp} @ {today_date_str} | PnL: ₹{trade['realized_pnl']:.2f}\n\n"
                continue
                
            current_profit = today_close - entry
            new_tsl = trade['tsl']
            
            if current_profit >= initial_risk:
                if new_tsl < entry:
                    new_tsl = entry
                    updated_tsl += 1
            elif current_profit >= (2 * initial_risk):
                trail_price = today_close - (0.5 * initial_risk)
                if trail_price > new_tsl:
                    new_tsl = round(trail_price, 2)
                    updated_tsl += 1

            trade['tsl'] = new_tsl
            trade['unrealized_pnl'] = (today_close - entry) * qty
            new_active_trades.append(trade)
            
            msg += (f"📈 *{trade['ticker']} OPEN*\n"
                    f"   LTP: ₹{today_close} @ {today_date_str} Close | Unrealized PnL: ₹{trade['unrealized_pnl']:.2f}\n"
                    f"   🛑 *New TSL for Tomorrow:* ₹{new_tsl}\n\n")
        except: 
            new_active_trades.append(trade)

    if closed_today == 0 and updated_tsl == 0: 
        msg += "🛡️ _No trades closed or updated today._"
    send_telegram(msg)
    update_github_file("active_trades.json", new_active_trades, sha_active)
    update_github_file("trade_history.json", history, sha_history)

def main():
    hour = NOW_IST.hour
    if 8 <= hour < 9: 
        run_pre_market_screener()
    elif 9 <= hour < 10: 
        run_green_flag_scan()
    elif 15 <= hour < 16: 
        run_post_market_manager()
    else: 
        run_pre_market_screener()

if __name__ == "__main__":
    main()
