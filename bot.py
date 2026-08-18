import os
import requests
import json
from datetime import datetime

# Load environment variables from GitHub Secrets
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
AI_API_KEY = os.getenv("AI_API_KEY")

def send_telegram_message(message):
    """Send formatted message to Telegram"""
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
    """Fetch live crypto prices from CoinGecko"""
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
    
    # DEBUG: Check if API key exists
    print(f"DEBUG: API Key exists: {bool(AI_API_KEY)}")
    print(f"DEBUG: API Key length: {len(AI_API_KEY) if AI_API_KEY else 0}")
    
    prompt = f"""You are a professional crypto swing trader specializing in technical analysis.

CURRENT MARKET PRICES:
- Bitcoin (BTC): {prices['BTC']:,.2f} USD
- Ethereum (ETH): {prices['ETH']:,.2f} USD
- Solana (SOL): {prices['SOL']:,.2f} USD
- Ripple (XRP): {prices['XRP']:,.4f} USD

TRADING RULES:
1. Maximum 1 trade per day across ALL assets
2. Only trade if confidence is above 80%
3. If no clear setup, recommend HOLD
4. Focus on risk-to-reward ratio (minimum 1:3)
5. Consider market trends and support/resistance levels

Provide your decision in this exact JSON format:
{{
    "action": "HOLD",
    "asset": "NONE",
    "confidence": 50,
    "reasoning": "Market is consolidating, waiting for clearer signals"
}}

OR if you see a strong setup:
{{
    "action": "BUY",
    "asset": "BTC",
    "confidence": 85,
    "reasoning": "Strong support bounce with high volume"
}}

Return ONLY valid JSON, no markdown formatting."""

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
        
        print(f"API Status Code: {response.status_code}")
        print(f"API Response: {response.text[:200]}")
        
        if response.status_code == 401:
            return {
                "action": "HOLD",
                "asset": "NONE",
                "confidence": 0,
                "reasoning": "Authentication failed. Check your API key in GitHub Secrets."
            }
        elif response.status_code != 200:
            return {
                "action": "HOLD",
                "asset": "NONE",
                "confidence": 0,
                "reasoning": f"API Error: {response.status_code}"
            }
        
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            # Clean up response
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
                "reasoning": "No AI response received"
            }
            
    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        return {
            "action": "HOLD",
            "asset": "NONE",
            "confidence": 0,
            "reasoning": "Failed to parse AI response"
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
    """Main bot execution"""
    print(" Trading Bot Started")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Get prices
    print("Fetching prices...")
    prices = get_prices()
    print(f"BTC: {prices['BTC']}, ETH: {prices['ETH']}, SOL: {prices['SOL']}, XRP: {prices['XRP']}")
    
    # Step 2: Get AI decision
    print("Asking Nemotron 3 Ultra AI...")
    decision = get_ai_decision(prices)
    print(f"Decision: {decision}")
    
    # Step 3: Format Telegram message
    emoji = "" if decision.get('action', 'HOLD') != "HOLD" else "⏸️"
    
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
        f"⏰ _Next check in 24 hours_\n"
        f"💰 _Powered by Nemotron 3 Ultra (Free)_"
    )
    
    send_telegram_message(message)
    print("✅ Bot completed successfully!")

if __name__ == "__main__":
    main()
