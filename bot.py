import os
import requests
import json
import re
import base64
import math
from datetime import datetime, timedelta

# --- CONFIGURATION ---
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "duttas-clinic"
REPO_NAME = "mybotiphon"
FILE_PATH = "trade_book.json"

# --- RISK MANAGEMENT ---
STOP_LOSS_PCT = -5.0       # Stop Loss per trade
TAKE_PROFIT_PCT = 10.0     # Take Profit per trade
MAX_DAILY_LOSS_PCT = -5.0  # CIRCUIT BREAKER: Max loss allowed per day (5% of $50 = $2.50)

POSITION_SIZES = {
    "LOW": 7.0,
    "MODERATE": 5.0,
    "HIGH": 3.0,
    "VERY HIGH": 1.0,
    "ERROR": 2.0
}

COINDCX_SYMBOL_MAP = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "XRP": "XRPUSDT"}
CG_ID_MAP = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple"}

# --- TELEGRAM & GITHUB FUNCTIONS ---
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

# --- TECHNICAL INDICATORS ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    return round(100 - (100 / (1 + (avg_gain / avg_loss))), 2)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow + signal: return 0, 0, "NEUTRAL"
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema = [data[0]]
        for i in range(1, len(data)): ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
        return ema
    ema_fast, ema_slow = ema(prices, fast), ema(prices, slow)
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
    signal_line = ema(macd_line, signal)
    histogram = macd_line[-1] - signal_line[-1]
    trend = "BULLISH" if histogram > 0 else ("BEARISH" if histogram < 0 else "NEUTRAL")
    return round(macd_line[-1], 2), round(histogram, 2), trend

def calculate_atr(candles, period=14):
    if len(candles) < period + 1: return 0
    true_ranges = []
    for i in range(1, len(candles)):
        high, low, prev_close = candles[i][2], candles[i][3], candles[i-1][4]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return round(sum(true_ranges[-period:]) / period, 2)

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    if len(prices) < period: return 0, 0, 0, "NEUTRAL"
    middle_band = sum(prices[-period:]) / period
    variance = sum((p - middle_band) ** 2 for p in prices[-period:]) / period
    std = math.sqrt(variance)
    upper_band, lower_band = middle_band + (std_dev * std), middle_band - (std_dev * std)
    width = ((upper_band - lower_band) / middle_band) * 100
    state = "EXPANDING" if width > 10 else ("SQUEEZING" if width < 3 else "NORMAL")
    return round(upper_band, 2), round(lower_band, 2), round(width, 2), state

def calculate_volatility_percent(candles, period=14):
    if len(candles) < period + 1: return 0
    returns = [(candles[i][4] - candles[i-1][4]) / candles[i-1][4] for i in range(1, len(candles))]
    mean_ret = sum(returns[-period:]) / period
    variance = sum((r - mean_ret) ** 2 for r in returns[-period:]) / period
    return round(math.sqrt(variance) * math.sqrt(365) * 100, 2)

# --- DATA FETCHING ---
def get_coindcx_price(symbol):
    try:
        pair = COINDCX_SYMBOL_MAP[symbol]
        response = requests.get(f"https://api.coindcx.com/exchange/v1/ticker?market={pair}", timeout=10).json()
        if isinstance(response, list) and len(response) > 0: return float(response[0]['last_price'])
    except: pass
    return None

def get_coingecko_candles(symbol):
    cg_id = CG_ID_MAP[symbol]
    response = requests.get(f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days=30", timeout=15).json()
    candles = [[c[0], c[1], c[2], c[3], c[4]] for c in response]
    prices = [c[4] for c in candles]
    return candles, prices

def get_fear_greed_index():
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10).json()
        if 'data' in response and len(response['data']) > 0:
            return int(response['data'][0]['value']), response['data'][0]['value_classification']
    except: pass
    return 50, "NEUTRAL"

def get_technical_data():
    technicals = {}
    for symbol, cg_id in CG_ID_MAP.items():
        try:
            candles, prices = get_coingecko_candles(symbol)
            coindcx_price = get_coindcx_price(symbol)
            current_price = coindcx_price if coindcx_price else prices[-1]
            market_data = requests.get(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={cg_id}", timeout=10).json()[0]
            
            rsi = calculate_rsi(prices)
            _, _, macd_trend = calculate_macd(prices)
            atr = calculate_atr(candles)
            _, _, bb_width, bb_state = calculate_bollinger_bands(prices)
            volatility_pct = calculate_volatility_percent(candles)
            
            vol_level = "VERY HIGH" if volatility_pct > 80 else ("HIGH" if volatility_pct > 50 else ("MODERATE" if volatility_pct > 30 else "LOW"))
            
            technicals[symbol] = {
                "price": current_price, "rsi": rsi, "macd_trend": macd_trend, "atr": atr,
                "bb_width": bb_width, "bb_state": bb_state, "volatility_pct": volatility_pct,
                "vol_level": vol_level, "change_24h": market_data['price_change_percentage_24h']
            }
        except Exception as e:
            print(f"Error for {symbol}: {e}")
            technicals[symbol] = {"price": 0, "rsi": 50, "macd_trend": "ERROR", "atr": 0, "bb_width": 0, "bb_state": "ERROR", "volatility_pct": 0, "vol_level": "ERROR", "change_24h": 0}
    return technicals

# --- AI DECISION ---
def get_ai_decision(technicals, has_open_trade, fear_greed_value, fear_greed_class):
    status_text = "You have an OPEN trade. Recommend SELL to exit, or HOLD." if has_open_trade else "No open trades. Recommend BUY or HOLD."
    prompt = f"""You are a professional crypto swing trader.
{status_text}
MARKET SENTIMENT: Fear & Greed Index: {fear_greed_value} ({fear_greed_class})
TECHNICALS:
- BTC: ${technicals['BTC']['price']:,.2f} (24h: {technicals['BTC']['change_24h']:.2f}%) | RSI: {technicals['BTC']['rsi']} | MACD: {technicals['BTC']['macd_trend']} | Vol: {technicals['BTC']['volatility_pct']}% ({technicals['BTC']['vol_level']}) | BB: {technicals['BTC']['bb_state']}
- ETH: ${technicals['ETH']['price']:,.2f} (24h: {technicals['ETH']['change_24h']:.2f}%) | RSI: {technicals['ETH']['rsi']} | MACD: {technicals['ETH']['macd_trend']} | Vol: {technicals['ETH']['volatility_pct']}% ({technicals['ETH']['vol_level']}) | BB: {technicals['ETH']['bb_state']}
- SOL: ${technicals['SOL']['price']:,.2f} (24h: {technicals['SOL']['change_24h']:.2f}%) | RSI: {technicals['SOL']['rsi']} | MACD: {technicals['SOL']['macd_trend']} | Vol: {technicals['SOL']['volatility_pct']}% ({technicals['SOL']['vol_level']}) | BB: {technicals['SOL']['bb_state']}
- XRP: ${technicals['XRP']['price']:,.4f} (24h: {technicals['XRP']['change_24h']:.2f}%) | RSI: {technicals['XRP']['rsi']} | MACD: {technicals['XRP']['macd_trend']} | Vol: {technicals['XRP']['volatility_pct']}% ({technicals['XRP']['vol_level']}) | BB: {technicals['XRP']['bb_state']}
RULES: 1. RSI < 30 + Fear < 30 = BUY. 2. RSI > 70 + Greed > 70 = SELL. 3. Max 1 trade/day, confidence > 80%. 4. AVOID if Volatility is VERY HIGH.
Reply ONLY with JSON: {{"action": "HOLD/BUY/SELL", "asset": "NONE/BTC/ETH/SOL/XRP", "confidence": 0-100, "reasoning": "..."}}"""
    
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com"}
    data = {"model": "openrouter/free", "messages": [{"role": "user", "content": prompt}]}
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        content = res.json()['choices'][0]['message']['content']
        match = re.search(r'\{.*\}', content, re.DOTALL)
        return json.loads(match.group(0)) if match else {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "Format error"}
    except: return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "API Error"}

# --- RISK MANAGEMENT ---
def check_stop_loss_take_profit(book, technicals, today_str):
    closed_trades = []
    for trade in book['trades']:
        if trade['status'] == 'OPEN':
            current_price = technicals[trade['asset']]['price']
            entry_price = trade['entry_price']
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            if pnl_pct <= STOP_LOSS_PCT:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = current_price
                trade['realized_pnl'] = (current_price - entry_price) * trade['quantity']
                trade['unrealized_pnl'] = 0
                trade['exit_reason'] = f"STOP LOSS ({pnl_pct:.2f}%)"
                trade['close_date'] = today_str
                closed_trades.append(f"🛑 SL Hit: {trade['asset']} ({pnl_pct:.2f}%)")
            elif pnl_pct >= TAKE_PROFIT_PCT:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = current_price
                trade['realized_pnl'] = (current_price - entry_price) * trade['quantity']
                trade['unrealized_pnl'] = 0
                trade['exit_reason'] = f"TAKE PROFIT (+{pnl_pct:.2f}%)"
                trade['close_date'] = today_str
                closed_trades.append(f"🎯 TP Hit: {trade['asset']} (+{pnl_pct:.2f}%)")
    return closed_trades

# --- MAIN EXECUTION ---
def main():
    print("Bot Started with Circuit Breaker")
    book, sha = get_github_file()
    technicals = get_technical_data()
    fear_greed_value, fear_greed_class = get_fear_greed_index()
    
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    today_str = ist_now.strftime("%Y-%m-%d")
    current_hour_ist = ist_now.hour
    
    # 1. Check SL/TP
    sl_tp_messages = check_stop_loss_take_profit(book, technicals, today_str)
    
    # 2. Calculate Daily Realized PnL
    daily_realized_pnl = sum(t.get('realized_pnl', 0) for t in book['trades'] if t.get('close_date') == today_str)
    daily_pnl_pct = (daily_realized_pnl / book['initial_capital']) * 100
    
    # 3. CIRCUIT BREAKER CHECK
    circuit_breaker_triggered = daily_pnl_pct <= MAX_DAILY_LOSS_PCT
    
    # 4. Calculate Unrealized PnL
    total_unrealized = sum((technicals[t['asset']]['price'] - t['entry_price']) * t['quantity'] for t in book['trades'] if t['status'] == 'OPEN')

    # 5. Get AI Decision (Skip if Circuit Breaker is active)
    if circuit_breaker_triggered:
        action = "HOLD"
        asset = "NONE"
        decision = {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": f"🚨 CIRCUIT BREAKER: Daily loss limit reached ({daily_pnl_pct:.2f}%). Trading paused for 24h."}
        print("CIRCUIT BREAKER TRIGGERED. No new trades.")
    else:
        has_open = any(t['status'] == 'OPEN' for t in book['trades'])
        decision = get_ai_decision(technicals, has_open, fear_greed_value, fear_greed_class)
        action = decision['action'].upper()
        asset = decision['asset'].upper()

    # 6. Execute Trade Logic
    new_trade_message = ""
    if action == 'BUY' and not any(t['status'] == 'OPEN' for t in book['trades']) and asset in ['BTC', 'ETH', 'SOL', 'XRP']:
        if book.get('last_trade_date') == today_str:
            action = 'HOLD'
            decision['reasoning'] = "Already traded today."
        else:
            price = technicals[asset]['price']
            vol_level = technicals[asset]['vol_level']
            position_size = POSITION_SIZES.get(vol_level, 5.0)
            quantity = position_size / price
            sl_price = price * (1 + STOP_LOSS_PCT / 100)
            tp_price = price * (1 + TAKE_PROFIT_PCT / 100)
            
            book['trades'].append({
                "id": len(book['trades']) + 1, "asset": asset, "action": "BUY", "entry_price": price,
                "quantity": quantity, "position_size": position_size, "status": "OPEN",
                "exit_price": None, "realized_pnl": 0, "unrealized_pnl": 0,
                "stop_loss": sl_price, "take_profit": tp_price, "exit_reason": None
            })
            book['last_trade_date'] = today_str
            new_trade_message = f"\n🆕 *New Trade*: BUY {asset} @ ${price:,.2f}\n   Size: ${position_size:.2f} | SL: ${sl_price:,.2f} | TP: ${tp_price:,.2f}"

    elif action == 'SELL' and any(t['status'] == 'OPEN' for t in book['trades']):
        for trade in book['trades']:
            if trade['status'] == 'OPEN' and trade['asset'] == asset:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = technicals[asset]['price']
                trade['realized_pnl'] = trade['unrealized_pnl']
                trade['unrealized_pnl'] = 0
                trade['exit_reason'] = "AI SELL SIGNAL"
                trade['close_date'] = today_str

    # 7. Save
    update_github_file(book, sha)
    
    total_realized = sum(t['realized_pnl'] for t in book['trades'])
    sl_tp_text = "\n".join(sl_tp_messages) if sl_tp_messages else ""
    
    # 8. Build Message
    if current_hour_ist >= 16:
        msg = (f"📊 *End of Day Trade Book*\n\n"
               f"💰 *Capital*: $50.00\n"
               f"📈 *Total Realized PnL*: ${total_realized:,.2f}\n"
               f"👻 *Unrealized PnL*: ${total_unrealized:,.2f}\n"
               f" *Today's PnL*: ${daily_realized_pnl:,.2f} ({daily_pnl_pct:.2f}%)\n"
               f" *Fear & Greed*: {fear_greed_value} ({fear_greed_class})\n\n"
               f"{sl_tp_text}{new_trade_message}\n\n"
               f"🧠 *Last AI Action*: {action} {asset}\n"
               f"📝 *Reasoning*: {decision['reasoning']}\n\n"
               f"⏰ _Market closes for today._")
    else:
        cb_warning = " *CIRCUIT BREAKER ACTIVE: Daily loss limit reached. No new trades today.*\n\n" if circuit_breaker_triggered else ""
        msg = (f"📊 *Volatility & Sentiment Report*\n\n"
               f"{cb_warning}"
               f"🧠 *Fear & Greed*: {fear_greed_value} ({fear_greed_class})\n"
               f"📉 *Today's PnL*: ${daily_realized_pnl:,.2f} ({daily_pnl_pct:.2f}%)\n\n"
               f"*BTC*: ${technicals['BTC']['price']:,.2f} | RSI: {technicals['BTC']['rsi']} | Vol: {technicals['BTC']['vol_level']}\n"
               f"*ETH*: ${technicals['ETH']['price']:,.2f} | RSI: {technicals['ETH']['rsi']} | Vol: {technicals['ETH']['vol_level']}\n"
               f"*SOL*: ${technicals['SOL']['price']:,.2f} | RSI: {technicals['SOL']['rsi']} | Vol: {technicals['SOL']['vol_level']}\n"
               f"*XRP*: ${technicals['XRP']['price']:,.4f} | RSI: {technicals['XRP']['rsi']} | Vol: {technicals['XRP']['vol_level']}\n\n"
               f"{sl_tp_text}{new_trade_message}"
               f"🧠 *AI Action*: {action} {asset}\n"
               f"🎯 *Confidence*: {decision.get('confidence', 0)}%\n"
               f"📝 *Reasoning*: {decision['reasoning']}\n\n"
               f"⏰ _Next check in 4 hours_")
               
    send_telegram_message(msg)
    print("Done!")

if __name__ == "__main__":
    main()
