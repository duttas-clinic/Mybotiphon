import os
import requests
import json
from datetime import datetime

# 1. Load Keys
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
        print("Telegram sent successfully.")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_prices():
    """Fetches prices for BTC, ETH, SOL, XRP"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,ethereum,ripple&vs_currencies=usd"
    res = requests.get(url).json()
    return {
        "BTC": res['bitcoin']['usd'],
        "ETH": res['ethereum']['usd'],
        "SOL": res['solana']['usd'],
        "XRP": res['ripple']['usd']
    }

def get_ai_decision(prices):
    """Sends data to OpenRouter AI (Llama 3.3 70B Free)"""
    prompt = f"""You are a conservative crypto swing trader. 
    Current Prices: BTC ${prices['BTC']}, ETH ${prices['ETH']}, SOL ${prices['SOL']}, XRP ${prices['XRP']}.
    
    RULES:
    1. Maximum 1 trade per day across ALL assets.
    2. Only recommend a trade if confidence is > 80%.
    3. If no clear setup, return HOLD.
    
    Output strictly in JSON format:
    {{"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "Market is choppy."}}
    OR
    {{"action": "BUY", "asset": "SOL", "confidence": 85, "reasoning": "Strong support bounce."}}"""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    content = res.json()['choices'][0]['message']['content']
    return json.loads(content)

def main():
    print("🤖 Bot started...")
    prices = get_prices()
    print("Prices fetched. Asking AI...")
    
    decision = get_ai_decision(prices)
    
    # Format Message
    emoji = "🚀" if decision['action'] != "HOLD" else "⏸️"
    msg = (
        f"{emoji} *Daily AI Trading Report*\n\n"
        f"📊 *Prices*:\n"
        f"• BTC: ${prices['BTC']:,.2f}\n"
        f"• ETH: ${prices['ETH']:,.2f}\n"
        f"• SOL: ${prices['SOL']:,.2f}\n"
        f"• XRP: ${prices['XRP']:,.4f}\n\n"
        f"🧠 *AI Decision*: {decision['action']} {decision['asset']}\n"
        f"🎯 *Confidence*: {decision['confidence']}%\n"
        f"📝 *Reasoning*: {decision['reasoning']}\n\n"
        f"⏰ _Next check in 24 hours._"
    )
    
    send_telegram_message(msg)
    print("✅ Done.")

if __name__ == "__main__":
    main()
