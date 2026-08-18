import os
import requests
import json
from datetime import datetime

# Load environment variables
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram Status: {response.status_code}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,ethereum,ripple&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()
    return {
        "BTC": data['bitcoin']['usd'],
        "ETH": data['ethereum']['usd'],
        "SOL": data['solana']['usd'],
        "XRP": data['ripple']['usd']
    }

def get_ai_decision(prices):
    prompt = f"""You are a professional crypto swing trader.

CURRENT PRICES:
- BTC: {prices['BTC']:,.2f} USD
- ETH: {prices['ETH']:,.2f} USD
- SOL: {prices['SOL']:,.2f} USD
- XRP: {prices['XRP']:,.4f} USD

RULES:
1. Max 1 trade per day total.
2. Only trade if confidence > 80%.
3. Otherwise, say HOLD.

Return ONLY valid JSON like this:
{{"action": "HOLD", "asset": "NONE", "confidence": 50, "reasoning": "Market is choppy."}}
OR
{{"action": "BUY", "asset": "BTC", "confidence": 85, "reasoning": "Strong support bounce."}}"""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com"
    }
    
    # Using Llama 3.1 8B (Guaranteed Free and Fast)
    data = {
        "model": "openrouter/free",

        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        print(f"API Status: {response.status_code}")
        
        if response.status_code != 200:
            return {
                "action": "HOLD",
                "asset": "NONE",
                "confidence": 0,
                "reasoning": f"API Error: {response.status_code}"
            }
        
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            # Clean up markdown if the AI adds it
            content = content.strip()
            if '```json' in content:
                content = content.split('```json')[-1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[-1].strip()
            
            return json.loads(content)
        else:
            return {
                "action": "HOLD",
                "asset": "NONE",
                "confidence": 0,
                "reasoning": "No AI response"
            }
            
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "action": "HOLD",
            "asset": "NONE",
            "confidence": 0,
            "reasoning": f"Error: {str(e)[:50]}"
        }

def main():
    print("Bot Started")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    prices = get_prices()
    print(f"Prices: {prices}")
    
    print("Asking Llama 3.1 AI...")
    decision = get_ai_decision(prices)
    print(f"Decision: {decision}")
    
    emoji = "🚀" if decision.get('action', 'HOLD') != "HOLD" else "️"
    
    message = (
        f"{emoji} *Daily AI Trading Report*\n\n"
        f"*Live Prices:*\n"
        f"• BTC: {prices['BTC']:,.2f} USD\n"
        f"• ETH: {prices['ETH']:,.2f} USD\n"
        f"• SOL: {prices['SOL']:,.2f} USD\n"
        f"• XRP: {prices['XRP']:,.4f} USD\n\n"
        f"*AI Decision:*\n"
        f"Action: {decision.get('action', 'HOLD')} {decision.get('asset', '')}\n"
        f"🎯 Confidence: {decision.get('confidence', 0)}%\n"
        f"📝 Reasoning: {decision.get('reasoning', 'N/A')}\n\n"
        f" _Next check in 24 hours_\n"
        f"💰 _Powered by Llama 3.1 (Free)_"
    )
    
    send_telegram_message(message)
    print("✅ Done!")

if __name__ == "__main__":
    main()
