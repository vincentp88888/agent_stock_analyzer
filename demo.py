#!/usr/bin/env python
"""
Demo script showing stock analysis workflow with mock data.
This demonstrates how the agent generates BUY/SELL recommendations.
"""

from agent_stock_analyzer import StockAnalysisAgent
from unittest.mock import patch, MagicMock
import json

# Create agent instance
agent = StockAnalysisAgent()

print("=" * 70)
print("STOCK ANALYSIS AGENT - DEMO WITH MOCK DATA")
print("=" * 70)
print(f"\nAgent Configuration:")
print(f"  - Ollama Host: {agent.ollama_host}")
print(f"  - Ollama Model: {agent.ollama_model}")
print(f"  - Stocks to analyze: {', '.join(agent.stocks[:3])}... (11 total)")
print(f"  - WhatsApp: {'ENABLED' if agent.enable_whatsapp_send else 'DISABLED'}")
print("\n" + "=" * 70)

# Mock data for demonstration
mock_stock_data = {
    "symbol": "QQQ",
    "current_price": 380.50,
    "prev_close": 375.20,
    "price_change_pct": 1.41,
    "volume": 42500000,
    "high_5d": 382.00,
    "low_5d": 374.00,
    "history": {
        "Close": {str(i): 370 + (i * 0.5) for i in range(20)}
    }
}

# Calculate technical indicators
print("\n📊 TECHNICAL ANALYSIS")
print("-" * 70)
indicators = agent.calculate_technical_indicators(mock_stock_data)
print(f"Symbol: {mock_stock_data['symbol']}")
print(f"Current Price: ${mock_stock_data['current_price']:.2f}")
print(f"Price Change: {mock_stock_data['price_change_pct']:.2f}%")
print(f"Volume: {mock_stock_data['volume']:,}")
print(f"\nTechnical Indicators:")
print(f"  - SMA 5: ${indicators.get('sma_5', 'N/A'):.2f}" if isinstance(indicators.get('sma_5'), (int, float)) else f"  - SMA 5: {indicators.get('sma_5', 'N/A')}")
print(f"  - SMA 20: ${indicators.get('sma_20', 'N/A'):.2f}" if isinstance(indicators.get('sma_20'), (int, float)) else f"  - SMA 20: {indicators.get('sma_20', 'N/A')}")
print(f"  - RSI: {indicators.get('rsi', 'N/A'):.2f}" if isinstance(indicators.get('rsi'), (int, float)) else f"  - RSI: {indicators.get('rsi', 'N/A')}")
print(f"  - 5-Day Momentum: {indicators.get('momentum_5d', 'N/A'):.2f}" if isinstance(indicators.get('momentum_5d'), (int, float)) else f"  - 5-Day Momentum: {indicators.get('momentum_5d', 'N/A')}")

# Demonstrate AI analysis with mock Ollama response
print("\n" + "=" * 70)
print("🤖 AI ANALYSIS (via Ollama qwen2.5:7b)")
print("-" * 70)

# Mock Ollama response for BUY signal
mock_ollama_response = {
    "recommendation": "BUY",
    "confidence": "HIGH",
    "target_price": 400.00,
    "reasoning": "Strong uptrend with breakout above 380. RSI above 60 indicates bullish momentum. Moving averages are aligned bullishly (SMA5 > SMA20). Volume increasing. Good entry point for long position."
}

print(f"\nMock Ollama Response (qwen2.5:7b):")
print(f"  Recommendation: {mock_ollama_response['recommendation']}")
print(f"  Confidence: {mock_ollama_response['confidence']}")
print(f"  Target Price: ${mock_ollama_response['target_price']:.2f}")
print(f"  Reasoning: {mock_ollama_response['reasoning']}")

# Demonstrate analysis for SELL signal
print("\n" + "=" * 70)
print("EXAMPLE: BEARISH STOCK ANALYSIS")
print("-" * 70)

bearish_stock = {
    "symbol": "DXYZ",
    "current_price": 85.25,
    "prev_close": 95.50,
    "price_change_pct": -10.75,
    "volume": 62500000,
    "high_5d": 98.00,
    "low_5d": 84.50,
}

print(f"\nSymbol: {bearish_stock['symbol']}")
print(f"Current Price: ${bearish_stock['current_price']:.2f}")
print(f"Price Change: {bearish_stock['price_change_pct']:.2f}%  ⚠️")
print(f"Volume: {bearish_stock['volume']:,}")

mock_sell_response = {
    "recommendation": "SELL",
    "confidence": "HIGH",
    "target_price": 75.00,
    "reasoning": "Strong bearish trend with significant price decline. RSI below 30 indicates oversold conditions. Price breaking below key support levels. High volume on down days. Consider taking losses or waiting for reversal confirmation."
}

print(f"\nMock Ollama Analysis:")
print(f"  Recommendation: 🔴 {mock_sell_response['recommendation']}")
print(f"  Confidence: {mock_sell_response['confidence']}")
print(f"  Target Price: ${mock_sell_response['target_price']:.2f}")
print(f"  Reasoning: {mock_sell_response['reasoning']}")

# Summary report
print("\n" + "=" * 70)
print("📋 REPORT SUMMARY")
print("-" * 70)

summary = """
✅ BUY SIGNALS: 1
   - QQQ: Strong uptrend, buy on dips

🔴 SELL SIGNALS: 1
   - DXYZ: Bearish trend, exit positions

⏸️ HOLD: 9
   - Other stocks showing neutral signals

This report would be sent to WhatsApp +6587533570 via Twilio

Detailed recommendations would follow for each BUY signal with:
  - Current price
  - Target price
  - Confidence level
  - Technical reasoning
"""

print(summary)

print("=" * 70)
print("✨ Demo Complete!")
print("=" * 70)
print("\nTo run the full agent with real data:")
print("  python agent_stock_analyzer.py           # Run once")
print("  python agent_stock_analyzer.py schedule  # Run every hour")
print("\nTo run tests:")
print("  python -m pytest test_agent_stock_analyzer.py -v")
print("\nConfiguration:")
print("  - Copy .env.example to .env and add your Twilio credentials")
print("  - Enable WhatsApp: ENABLE_WHATSAPP_SEND=true")
print("=" * 70)
