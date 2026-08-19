import os
import requests
import json
import re
import base64
from datetime import datetime, timedelta

# Load environment variables
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "duttas-clinic"
REPO_NAME = "mybotiphon"
FILE_PATH = "trade_book.json"

COIN_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT"
}

CG_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple"
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_github_file():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers).json()
    content = base64.b64decode(response['content']).decode('utf-8')
    return json.loads(content), response['sha']

def update_github_file(data, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content = base64.b64encode(json.dumps(data, indent=2).encode('utf-8')).decode('utf-8')
    payload = {"message": "Update trade book", "content": content, "sha": sha}
    requests.put(url, headers=headers, json=payload)

def calculate_rsi(prices, period=14):
    """Calculate RSI from a list of closing prices"""
    if len(prices) < period + 1:
        return 50
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD from a list of closing prices"""
    if len(prices) < slow + signal:
        return 0, 0, "NEUTRAL"
    
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
        return ema
    
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
    signal_line = ema(macd_line, signal)
    
    current_macd = macd_line[-1]
    current_signal = signal_line[-1]
    histogram = current_macd - current_signal
    
    if histogram > 0:
        trend = "BULLISH"
    elif histogram < 0:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
    
    return round(current_macd, 2), round(histogram, 2), trend

def get_technical_data():
    """Fetches OHLCV data from Binance and calculates RSI + MACD"""
    technicals = {}
    
    for symbol, binance_pair in COIN_MAP.items():
        # Fetch 100 candles (4h timeframe) from Binance
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_pair}&interval=4h&limit=100"
        response = requests.get(url).json()
        
        # Extract closing prices
        closes = [float(candle[4]) for candle in response]
        current_price = closes[-1]
        
        # Calculate indicators
        rsi = calculate_rsi(closes)
        macd, histogram, trend = calculate_macd(closes)
        
        technicals[symbol] = {
            "price": current_price,
            "rsi": rsi,
            "macd": macd,
            "histogram": histogram,
            "trend": trend
        }
    
    return technicals

def get_ai_decision(technicals, has_open_trade):
    status_text = "You have an OPEN trade. Recommend SELL to exit, or HOLD." if has_open_trade else "No open trades. Recommend BUY or HOLD."
    
    prompt = f"""You are a professional crypto swing trader with expertise in technical analysis.
{status_text}

TECHNICAL INDICATORS (4h Timeframe):
- BTC: Price ${technicals['BTC']['price']:,.2f} | RSI: {technicals['BTC']['rsi']} | MACD: {technicals['BTC']['trend']} (Hist: {technicals['BTC']['histogram']})
- ETH: Price ${technicals['ETH']['price']:,.2f} | RSI: {technicals['ETH']['rsi']} | MACD: {technicals['ETH']['trend']} (Hist: {technicals['ETH']['histogram']})
- SOL: Price ${technicals['SOL']['price']:,.2f} | RSI: {technicals['SOL']['rsi']} | MACD: {technicals['SOL']['trend']} (Hist: {technicals['SOL']['histogram']})
- XRP: Price ${technicals['XRP']['price']:,.4f} | RSI: {technicals['XRP']['rsi']} | MACD: {technicals['XRP']['trend']} (Hist: {technicals['XRP']['histogram']})

TECHNICAL ANALYSIS RULES:
1. RSI < 30 = Oversold (potential BUY)
2. RSI > 70 = Overbought (potential SELL)
3. MACD Bullish crossover = BUY signal
4. MACD Bearish crossover = SELL signal
5. Max 1 trade per day, confidence > 80%

Reply ONLY with JSON:
{{"action": "HOLD", "asset": "NONE", "confidence": 50, "reasoning": "RSI neutral at 52, MACD flat."}}
OR
{{"action": "BUY", "asset": "SOL", "confidence": 85, "reasoning": "RSI oversold at 28, MACD bullish crossover."}}
OR
{{"action": "SELL", "asset": "BTC", "confidence": 90, "reasoning": "RSI overbought at 72, MACD bearish divergence."}}"""

    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com"}
    data = {"model": "openrouter/free", "messages": [{"role": "user", "content": prompt}]}
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        content = res.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        return json.loads(match.group(0)) if match else {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "Format error"}
    except:
        return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "API Error"}

def main():
    print("Bot Started with Technical Indicators")
    book, sha = get_github_file()
    technicals = get_technical_data()
    
    # Calculate IST Time
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    today_str = ist_now.strftime("%Y-%m-%d")
    current_hour_ist = ist_now.hour
    
    # 1. Calculate Unrealized PnL
    total_unrealized = 0
    for trade in book['trades']:
        if trade['status'] == 'OPEN':
            cg_id = CG_ID_MAP.get(trade['asset'])
            if cg_id:
                current_price = technicals[trade['asset']]['price']
                trade['current_price'] = current_price
                trade['unrealized_pnl'] = (current_price - trade['entry_price']) * trade['quantity']
                total_unrealized += trade['unrealized_pnl']

    # 2. Get AI Decision
    has_open = any(t['status'] == 'OPEN' for t in book['trades'])
    decision = get_ai_decision(technicals, has_open)
    
    action = decision['action'].upper()
    asset = decision['asset'].upper()
    
    # 3. Execute Trade Logic
    if action == 'BUY' and not has_open and asset in ['BTC', 'ETH', 'SOL', 'XRP']:
        if book.get('last_trade_date') == today_str:
            action = 'HOLD'
            decision['reasoning'] = "Already traded today. Rule enforced."
        else:
            price = technicals[asset]['price']
            quantity = 5.0 / price 
            book['trades'].append({
                "id": len(book['trades']) + 1,
                "asset": asset, "action": "BUY", "entry_price": price, 
                "quantity": quantity, "status": "OPEN", "exit_price": None, "realized_pnl": 0
            })
            book['last_trade_date'] = today_str
            
    elif action == 'SELL' and has_open:
        for trade in book['trades']:
            if trade['status'] == 'OPEN' and trade['asset'] == asset:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = technicals[asset]['price']
                trade['realized_pnl'] = trade['unrealized_pnl']
                trade['unrealized_pnl'] = 0

    # 4. Save
    update_github_file(book, sha)
    
    total_realized = sum(t['realized_pnl'] for t in book['trades'])
    
    # 5. Send Message
    if current_hour_ist >= 16:
        msg = (f"📊 *End of Day Trade Book*\n\n"
               f"💰 *Capital*: $50.00\n"
               f"📈 *Realized PnL*: ${total_realized:,.2f}\n"
               f"👻 *Unrealized PnL*: ${total_unrealized:,.2f}\n\n"
               f"🧠 *Last AI Action*: {action} {asset}\n"
               f"📝 *Reasoning*: {decision['reasoning']}\n\n"
               f"⏰ _Market closes for today._")
    else:
        msg = (f"📊 *Technical Analysis Report*\n\n"
               f"*BTC*: ${technicals['BTC']['price']:,.2f}\n"
               f"  RSI: {technicals['BTC']['rsi']} | MACD: {technicals['BTC']['trend']}\n"
               f"*ETH*: ${technicals['ETH']['price']:,.2f}\n"
               f"  RSI: {technicals['ETH']['rsi']} | MACD: {technicals['ETH']['trend']}\n"
               f"*SOL*: ${technicals['SOL']['price']:,.2f}\n"
               f"  RSI: {technicals['SOL']['rsi']} | MACD: {technicals['SOL']['trend']}\n"
               f"*XRP*: ${technicals['XRP']['price']:,.4f}\n"
               f"  RSI: {technicals['XRP']['rsi']} | MACD: {technicals['XRP']['trend']}\n\n"
               f"🧠 *AI Action*: {action} {asset}\n"
               f"🎯 *Confidence*: {decision.get('confidence', 0)}%\n"
               f"📝 *Reasoning*: {decision['reasoning']}\n\n"
               f"⏰ _Next check in 4 hours_")
               
    send_telegram_message(msg)
    print("Done!")

if __name__ == "__main__":
    main()
