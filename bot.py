import os
import requests
import json
from datetime import datetime

# Load environment variables
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")

def send_telegram_message(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram sent: {response.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_prices():
    """Fetch live prices for BTC, ETH, SOL, XRP"""
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
    """Get trading decision from Nemotron 3 Ultra (FREE)"""
    
    prompt = f"""You are a conservative crypto swing trader with expertise in technical analysis.

Current Market Prices:
- Bitcoin (BTC): ${prices['BTC']:,.2f}
- Ethereum (ETH): ${prices['ETH']:,.2f}
- Solana (SOL): ${prices['SOL']:,.2f}
- Ripple (XRP): ${prices['XRP']:,.4f}

TRADING RULES:
1. Maximum 1 trade per day across ALL assets
2. Only recommend a trade if confidence is above 80%
3. If no clear setup, recommend HOLD
4. Focus on risk-to-reward ratio (minimum 1:3)
5. Consider current market conditions and trends

Provide your analysis and decision in this JSON format:
{{
    "action": "HOLD" or "BUY" or "SELL",
    "asset": "BTC" or "ETH" or "SOL" or "XRP" or "NONE",
    "confidence": number between 0-100,
    "reasoning": "Brief explanation of your analysis"
}}

Return ONLY valid JSON, no additional text."""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com"
    }
    
    data = {
        "model": "nvidia/nemotron-3-ultra:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=90
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
            # Clean up the response
            content = content.strip()
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            return json.loads(content)
        else:
            return {
                "action": "HOLD",
                "asset": "NONE",
                "confidence": 0,
                "reasoning": "No AI response received"
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
    """Main function to run the trading bot"""
    print(" Trading Bot Started...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Get live prices
    print("📊 Fetching prices...")
    prices = get_prices()
    print(f"Prices: BTC <LaTex>id_1</LaTex>{prices['ETH']}, SOL <LaTex>id_2</LaTex>{prices['XRP']}")
    
    # Step 2: Get AI decision
    print("🧠 Asking Nemotron 3 Ultra AI...")
    decision = get_ai_decision(prices)
    print(f"Decision: {decision}")
    
    # Step 3: Format and send Telegram message
    emoji = "🚀" if decision.get('action', 'HOLD') != "HOLD" else "⏸️"
    
    message = (
        f"{emoji} *Daily AI Trading Report*\n\n"
        f" *Live Prices:*\n"
        f"• BTC: <LaTex>id_3</LaTex>{prices['ETH']:,.2f}\n"
        f"• SOL: <LaTex>id_4</LaTex>{prices['XRP']:,.4f}\n\n"
        f" *AI Decision:*\n"
        f"Action: {decision.get('action', 'HOLD')} {decision.get('asset', '')}\n"
        f"🎯 Confidence: {decision.get('confidence', 0)}%\n"
        f"📝 Reasoning: {decision.get('reasoning', 'N/A')}\n\n"
        f"⏰ _Next check in 24 hours_\n"
        f"💰 _Powered by Nemotron 3 Ultra (Free)_"
    )
    
    send_telegram_message(message)
    print("✅ Bot completed successfully!")

if __name__ == "__main__":
    main()
