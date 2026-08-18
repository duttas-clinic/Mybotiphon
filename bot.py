import os
import requests
import json
import re
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

def get_market_data():
    """Fetches Price, 24h Change %, and 24h Volume from CoinGecko"""
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,solana,ripple&order=market_cap_desc&per_page=100&page=1&sparkline=false"
    response = requests.get(url)
    data = response.json()
    
    market_info = {}
    for coin in data:
        cid = coin['id']
        if cid == 'bitcoin': market_info['BTC'] = coin
        elif cid == 'ethereum': market_info['ETH'] = coin
        elif cid == 'solana': market_info['SOL'] = coin
        elif cid == 'ripple': market_info['XRP'] = coin
        
    return market_info

def get_ai_decision(market_info):
    prompt = f"""You are a professional crypto swing trader.

CURRENT MARKET DATA:
- BTC: Price {market_info['BTC']['current_price']:,.2f} USD | 24h Change: {market_info['BTC']['price_change_percentage_24h']:.2f}% | Vol: {market_info['BTC']['total_volume']:,.0f}
- ETH: Price {market_info['ETH']['current_price']:,.2f} USD | 24h Change: {market_info['ETH']['price_change_percentage_24h']:.2f}% | Vol: {market_info['ETH']['total_volume']:,.0f}
- SOL: Price {market_info['SOL']['current_price']:,.2f} USD | 24h Change: {market_info['SOL']['price_change_percentage_24h']:.2f}% | Vol: {market_info['SOL']['total_volume']:,.0f}
- XRP: Price {market_info['XRP']['current_price']:,.4f} USD | 24h Change: {market_info['XRP']['price_change_percentage_24h']:.2f}% | Vol: {market_info['XRP']['total_volume']:,.0f}

TRADING RULES:
1. Max 1 trade per day total across all assets.
2. Look for high volume breakouts or oversold bounces.
3. Only trade if confidence is > 80%.
4. Otherwise, say HOLD.

You MUST reply with ONLY a JSON object. No other text.
Example: {{"action": "HOLD", "asset": "NONE", "confidence": 50, "reasoning": "Low volume, waiting for breakout."}}
OR
{{"action": "BUY", "asset": "SOL", "confidence": 85, "reasoning": "High volume breakout with strong 24h momentum."}}"""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com"
    }
    
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
        
        if response.status_code != 200:
            return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": f"API Error: {response.status_code}"}
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Smart JSON Parser
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        
        return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": "AI format error."}
            
    except Exception as e:
        return {"action": "HOLD", "asset": "NONE", "confidence": 0, "reasoning": f"Code Error: {str(e)[:50]}"}

def main():
    print("Bot Started with Technical Indicators")
    
    market_info = get_market_data()
    print("Market data fetched.")
    
    decision = get_ai_decision(market_info)
    print(f"Decision: {decision}")
    
    emoji = "🚀" if decision.get('action', 'HOLD') != "HOLD" else "⏸️"
    
    # Format the message with new data
    def format_coin(symbol, info):
        return (f"• {symbol}: {info['current_price']:,.2f} USD\n"
                f"  📈 24h: {info['price_change_percentage_24h']:.2f}% | Vol: {info['total_volume']:,.0f}\n")

    message = (
        f"{emoji} *Daily AI Trading Report*\n\n"
        f"*Market Data:*\n"
        f"{format_coin('BTC', market_info['BTC'])}"
        f"{format_coin('ETH', market_info['ETH'])}"
        f"{format_coin('SOL', market_info['SOL'])}"
        f"{format_coin('XRP', market_info['XRP'])}\n"
        f"*AI Decision:*\n"
        f"Action: {decision.get('action', 'HOLD')} {decision.get('asset', '')}\n"
        f"🎯 Confidence: {decision.get('confidence', 0)}%\n"
        f"📝 Reasoning: {decision.get('reasoning', 'N/A')}\n\n"
        f"⏰ _Next check in 8 hours_\n"
        f"💰 _Powered by OpenRouter Free AI_"
    )
    
    send_telegram_message(message)
    print("✅ Done!")

if __name__ == "__main__":
    main()
