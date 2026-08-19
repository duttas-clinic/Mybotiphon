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

# Translator for CoinGecko IDs
COIN_MAP = {
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

def get_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,solana,ripple"
    return {c['id']: c for c in requests.get(url).json()}

def get_ai_decision(market_info, has_open_trade):
    status_text = "You have an OPEN trade. Recommend SELL to exit, or HOLD." if has_open_trade else "No open trades. Recommend BUY or HOLD."
    
    prompt = f"""You are a professional crypto swing trader.
{status_text}

CURRENT MARKET DATA:
- BTC: {market_info['bitcoin']['current_price']:,.2f} USD (24h: {market_info['bitcoin']['price_change_percentage_24h']:.2f}%)
- ETH: {market_info['ethereum']['current_price']:,.2f} USD (24h: {market_info['ethereum']['price_change_percentage_24h']:.2f}%)
- SOL: {market_info['solana']['current_price']:,.2f} USD (24h: {market_info['solana']['price_change_percentage_24h']:.2f}%)
- XRP: {market_info['ripple']['current_price']:,.4f} USD (24h: {market_info['ripple']['price_change_percentage_24h']:.2f}%)

RULES:
1. Max 1 trade per day.
2. Only trade if confidence > 80%.

Reply ONLY with JSON:
{{"action": "HOLD", "asset": "NONE", "confidence": 50, "reasoning": "Waiting."}}
OR
{{"action": "BUY", "asset": "BTC", "confidence": 85, "reasoning": "Breakout."}}
OR
{{"action": "SELL", "asset": "BTC", "confidence": 90, "reasoning": "Target hit."}}"""

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
    print("Bot Started")
    book, sha = get_github_file()
    market = get_market_data()
    
    # Calculate IST Time (UTC + 5:30)
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    today_str = ist_now.strftime("%Y-%m-%d")
    current_hour_ist = ist_now.hour
    
    # 1. Calculate Unrealized PnL
    total_unrealized = 0
    for trade in book['trades']:
        if trade['status'] == 'OPEN':
            cg_id = COIN_MAP.get(trade['asset'])
            if cg_id and cg_id in market:
                current_price = market[cg_id]['current_price']
                trade['current_price'] = current_price
                trade['unrealized_pnl'] = (current_price - trade['entry_price']) * trade['quantity']
                total_unrealized += trade['unrealized_pnl']

    # 2. Get AI Decision
    has_open = any(t['status'] == 'OPEN' for t in book['trades'])
    decision = get_ai_decision(market, has_open)
    
    action = decision['action'].upper()
    asset = decision['asset'].upper()
    
    # 3. Execute Trade Logic (Enforce 1 trade per day)
    if action == 'BUY' and not has_open and asset in ['BTC', 'ETH', 'SOL', 'XRP']:
        if book.get('last_trade_date') == today_str:
            action = 'HOLD'
            decision['reasoning'] = "Already traded today. Rule enforced."
        else:
            cg_id = COIN_MAP[asset]
            price = market[cg_id]['current_price']
            quantity = 5.0 / price 
            book['trades'].append({
                "id": len(book['trades']) + 1,
                "asset": asset, "action": "BUY", "entry_price": price, 
                "quantity": quantity, "status": "OPEN", "exit_price": None, "realized_pnl": 0
            })
            book['last_trade_date'] = today_str # Lock trades for today
            
    elif action == 'SELL' and has_open:
        for trade in book['trades']:
            if trade['status'] == 'OPEN' and trade['asset'] == asset:
                cg_id = COIN_MAP[asset]
                trade['status'] = 'CLOSED'
                trade['exit_price'] = market[cg_id]['current_price']
                trade['realized_pnl'] = trade['unrealized_pnl']
                trade['unrealized_pnl'] = 0

    # 4. Save
    update_github_file(book, sha)
    
    total_realized = sum(t['realized_pnl'] for t in book['trades'])
    
    # 5. Send Message (Full PnL report only at 5 PM IST, otherwise short update)
    if current_hour_ist >= 16: # 5 PM IST is 17:00, so >= 16 catches the 5 PM run
        msg = (f"📊 *End of Day Trade Book*\n\n"
               f"💰 *Capital*: $50.00\n"
               f"📈 *Realized PnL*: ${total_realized:,.2f}\n"
               f"👻 *Unrealized PnL*: ${total_unrealized:,.2f}\n\n"
               f"🧠 *Last AI Action*: {action} {asset}\n"
               f"📝 *Reasoning*: {decision['reasoning']}\n\n"
               f"⏰ _Market closes for today._")
    else:
        msg = (f" *Market Update*\n\n"
               f"BTC: {market['bitcoin']['current_price']:,.2f} ({market['bitcoin']['price_change_percentage_24h']:.2f}%)\n"
               f"ETH: {market['ethereum']['current_price']:,.2f} ({market['ethereum']['price_change_percentage_24h']:.2f}%)\n"
               f"SOL: {market['solana']['current_price']:,.2f} ({market['solana']['price_change_percentage_24h']:.2f}%)\n"
               f"XRP: {market['ripple']['current_price']:,.4f} ({market['ripple']['price_change_percentage_24h']:.2f}%)\n\n"
               f"🧠 *AI Action*: {action} {asset}\n"
               f"📝 *Reasoning*: {decision['reasoning']}\n\n"
               f"⏰ _Next check in 4 hours_")
               
    send_telegram_message(msg)
    print("Done!")

if __name__ == "__main__":
    main()
