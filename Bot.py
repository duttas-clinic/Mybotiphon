import os
import requests
import json
from datetime import datetime

# 1. Load environment variables (we will set these in GitHub Secrets)
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram_message(message):
    """Sends a message to your Telegram bot."""
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

def get_btc_price():
    """Fetches current BTC price from a free public API (Binance)."""
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    response = requests.get(url)
    data = response.json()
    return float(data['price'])

def mock_ai_decision(current_price):
    """
    TODO: Replace this with real OpenRouter/DeepSeek API call later.
    For now, this simulates the AI making a conservative decision.
    """
    # Simulating an 85% confidence HOLD to be safe on day 1
    return {
        "action": "HOLD",
        "confidence": 85,
        "reasoning": "Market consolidation detected. Waiting for clearer breakout. (Mock AI)"
    }

def main():
    print("🤖 Bot started at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Step 1: Get Market Data
    price = get_btc_price()
    print(f"Current BTC Price: ${price:,.2f}")
    
    # Step 2: Get AI Decision
    decision = mock_ai_decision(price)
    print(f"AI Decision: {decision['action']} (Confidence: {decision['confidence']}%)")
    
    # Step 3: Format and Send Telegram Alert
    emoji = "⏸️" if decision['action'] == "HOLD" else "🚀"
    message = (
        f"{emoji} *Daily Trading Bot Report*\n\n"
        f"📊 *Asset*: BTC/USDT\n"
        f"💰 *Current Price*: ${price:,.2f}\n"
        f"🧠 *AI Action*: {decision['action']}\n"
        f"🎯 *Confidence*: {decision['confidence']}%\n"
        f"📝 *Reasoning*: {decision['reasoning']}\n\n"
        f"⏰ _Next check in 24 hours._"
    )
    
    send_telegram_message(message)
    print("✅ Bot finished successfully.")

if __name__ == "__main__":
    main()
