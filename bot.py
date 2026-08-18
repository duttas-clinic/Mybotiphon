import os
import requests
import json
import re
from datetime import datetime

# 1. Load Keys
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload)
        print(f"Telegram Status: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,ethereum,ripple&vs_currencies=usd"
    res = requests.get(url).json()
    return {
        "BTC": res['bitcoin']['usd'],
        "ETH": res['ethereum']['usd'],
        "SOL": res['solana']['usd'],
        "XRP": res['ripple']['usd']
    }

def get_ai_decision(prices):
    prompt = f"""You are a conservative crypto swing trader.
Prices: BTC ${prices['BTC']}, ETH ${prices['ETH']}, SOL ${prices['SOL']}, XRP ${prices['XRP']}.

Rules: Max 1 trade/day. Only trade if confidence > 80%. Otherwise HOLD.
Return ONLY a JSON object at the very end of your response. No markdown formatting.
Example: {{"action": "HOLD", "asset": "NONE", "confidence": 50, "reasoning": "Market is choppy"}}"""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com"
    }
    
    # Using DeepSeek R1 Free via OpenRouter
    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        print(f"API Status: {res.status_code}")
        
        if res.status_code != 200:
            return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": f"API Error: {res.status_code} - {res.text[:100]}"}
        
        result = res.json()
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            
            # DeepSeek R1 uses  tags. We need to extract the JSON after them.
            if '' in content:
                content = content.split('')[-1]
            
            # Clean up any markdown formatting like ```json ... ```
            content = re.sub(r'```json\s*|\s*```', '', content).strip()
            
            return json.loads(content)
        else:
            return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "No AI response received."}
            
    except Exception as e:
        print(f"AI Error: {e}")
        return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": f"Code Error: {str(e)[:50]}"}

def main():
    print(" Bot started...")
    prices = get_prices()
    print(f"Prices: {prices}")
    print("Asking DeepSeek AI...")
    
    decision = get_ai_decision(prices)
    print(f"Decision: {decision}")
    
    emoji = "🚀" if decision.get('action', 'HOLD') != "HOLD" else "⏸️"
    msg = (
        f"{emoji} *Daily DeepSeek AI Report*\n\n"
        f" *Prices*:\n"
        f"• BTC: ${prices['BTC']:,.2f}\n"
        f"• ETH: ${prices['ETH']:,.2f}\n"
        f"• SOL: ${prices['SOL']:,.2f}\n"
        f"• XRP: ${prices['XRP']:,.4f}\n\n"
        f" *AI Decision*: {decision.get('action', 'HOLD')} {decision.get('asset', '')}\n"
        f"🎯 *Confidence*: {decision.get('confidence', 0)}%\n"
        f"📝 *Reasoning*: {decision.get('reasoning', 'N/A')}\n\n"
        f"⏰ _Next check in 24 hours._"
    )
    
    send_telegram_message(msg)
    print("✅ Done.")

if __name__ == "__main__":
    main()
