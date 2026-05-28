import asyncio
import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
import yfinance as yf
from dotenv import load_dotenv

try:
    import schedule
except ImportError:
    schedule = None

load_dotenv()

class StockAnalysisAgent:
    def __init__(self) -> None:
        self.stocks: List[str] = [
            "QQQ",
            "DXYZ",
            "VCX",
            "SOXX",
            "ROBO",
            "HST.SI",
            "2807.HK",
            "3174.HK",
            "2800.HK",
            "3188.HK",
            "ES3.SI",
        ]

        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "").strip()
        self.whatsapp_number: str = os.getenv("WHATSAPP_NUMBER", "6587533570").strip()
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip()

        # For WSL -> Windows Ollama
        self.ollama_host: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip()

        # Optional Twilio WhatsApp sending
        self.twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_whatsapp_from: str = os.getenv(
            "TWILIO_WHATSAPP_FROM",
            "whatsapp:+14155238886",
        ).strip()

        self.request_timeout: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
        self.symbol_pause_seconds: float = float(os.getenv("SYMBOL_PAUSE_SECONDS", "3"))
        self.max_tavily_results: int = int(os.getenv("MAX_TAVILY_RESULTS", "3"))
        self.enable_whatsapp_send: bool = os.getenv("ENABLE_WHATSAPP_SEND", "false").lower() == "true"
        
        # Analysis results
        self.analysis_results: List[Dict[str, Any]] = []

    def _now_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def format_price(self, price: Any) -> str:
        numeric = self._safe_float(price)
        if numeric is None:
            return "N/A"
        return f"${numeric:.2f}"

    def _find_ollama_command(self) -> Optional[List[str]]:
        candidates = [
            ["ollama"],
            ["/mnt/c/Users/Public/AppData/Local/Programs/Ollama/ollama.exe"],
            ["/mnt/c/Program Files/Ollama/ollama.exe"],
            ["ollama.exe"],
        ]

        for cmd in candidates:
            executable = cmd
            if executable in ("ollama", "ollama.exe"):
                found = shutil.which(executable)
                if found:
                    return [found]
            else:
                if os.path.exists(executable):
                    return cmd
        return None

    def query_ollama(self, prompt: str) -> str:
        """
        Query Ollama.
        Prefer HTTP API because Ollama is installed on Windows and WSL can call it.
        Fallback to CLI if available.
        """
        # First try HTTP API
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=180,
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", "")).strip()
        except Exception as http_err:
            # Fallback to CLI
            cli = self._find_ollama_command()
            if cli:
                try:
                    result = subprocess.run(
                        cli + ["run", self.ollama_model, prompt],
                        capture_output=True,
                        text=True,
                        timeout=180,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                    stderr = result.stderr.strip() if result.stderr else "Unknown CLI error"
                    return f'{{"recommendation":"HOLD","confidence":"LOW","reason":"Ollama CLI error: {stderr}","target_price":null}}'
                except Exception as cli_err:
                    return (
                        '{"recommendation":"HOLD","confidence":"LOW",'
                        f'"reason":"Ollama HTTP error: {str(http_err)}; CLI fallback error: {str(cli_err)}",'
                        '"target_price":null}'
                    )

            return (
                '{"recommendation":"HOLD","confidence":"LOW",'
                f'"reason":"Ollama HTTP error: {str(http_err)}",'
                '"target_price":null}'
            )

    def get_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch stock data using yfinance with safer handling.
        Avoid stock.info because it often triggers extra requests and rate limits.
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1d", auto_adjust=False)

            if hist is None or hist.empty:
                return {
                    "symbol": symbol,
                    "error": f"No price data returned for {symbol}",
                }

            close_series = hist["Close"].dropna() if "Close" in hist else []
            high_series = hist["High"].dropna() if "High" in hist else []
            low_series = hist["Low"].dropna() if "Low" in hist else []
            volume_series = hist["Volume"].dropna() if "Volume" in hist else []

            current_price = self._safe_float(close_series.iloc[-1]) if len(close_series) >= 1 else None
            prev_close = self._safe_float(close_series.iloc[-2]) if len(close_series) >= 2 else None
            high_5d = self._safe_float(high_series.max()) if len(high_series) >= 1 else None
            low_5d = self._safe_float(low_series.min()) if len(low_series) >= 1 else None
            volume = self._safe_float(volume_series.iloc[-1]) if len(volume_series) >= 1 else None

            # Calculate price change
            price_change = None
            price_change_pct = None
            if current_price is not None and prev_close is not None and prev_close != 0:
                price_change = current_price - prev_close
                price_change_pct = (price_change / prev_close) * 100

            return {
                "symbol": symbol,
                "current_price": current_price,
                "prev_close": prev_close,
                "price_change": price_change,
                "price_change_pct": price_change_pct,
                "volume": volume,
                "high_5d": high_5d,
                "low_5d": low_5d,
                "history": hist.tail(24).to_dict(),
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "error": f"Error fetching stock data: {str(e)}",
            }

    def calculate_technical_indicators(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate technical indicators like SMA, RSI, MACD from stock history.
        """
        try:
            if "history" not in stock_data or not stock_data["history"]:
                return {"symbol": stock_data.get("symbol"), "error": "No history available"}

            history = stock_data["history"]
            close_prices = history.get("Close", {})
            
            if not close_prices:
                return {"symbol": stock_data.get("symbol"), "error": "No close prices available"}

            # Convert to list of floats
            closes = [self._safe_float(v) for v in close_prices.values()]
            closes = [c for c in closes if c is not None]

            if len(closes) < 3:
                return {"symbol": stock_data.get("symbol"), "error": "Insufficient data for indicators"}

            # Simple Moving Average (SMA)
            sma_5 = sum(closes[-5:]) / min(5, len(closes)) if closes else None
            sma_20 = sum(closes[-20:]) / min(20, len(closes)) if closes else None

            # RSI (Relative Strength Index)
            rsi = self._calculate_rsi(closes)

            # Price momentum
            momentum_5d = closes[-1] - closes[0] if len(closes) >= 5 else 0

            return {
                "symbol": stock_data.get("symbol"),
                "sma_5": sma_5,
                "sma_20": sma_20,
                "rsi": rsi,
                "momentum_5d": momentum_5d,
            }
        except Exception as e:
            return {"symbol": stock_data.get("symbol"), "error": f"Indicator calculation error: {str(e)}"}

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI (Relative Strength Index)."""
        try:
            if len(prices) < period + 1:
                return None

            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas[-period:]]
            losses = [-d if d < 0 else 0 for d in deltas[-period:]]

            avg_gain = sum(gains) / period if period > 0 else 0
            avg_loss = sum(losses) / period if period > 0 else 0

            if avg_loss == 0:
                return 100 if avg_gain > 0 else 50

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception:
            return None

    def search_tavily(self, symbol: str) -> str:
        """
        Search for recent news and market sentiment about the stock using Tavily API.
        """
        if not self.tavily_api_key:
            return "No recent news (Tavily API key not configured)"

        try:
            query = f"{symbol} stock market analysis forecast"
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "max_results": self.max_tavily_results,
                "include_answer": True,
            }

            response = requests.post(
                "https://api.tavily.com/search",
                json=payload,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            data = response.json()

            answer = data.get("answer", "")
            if answer:
                return answer[:500]
            return "No recent news found"
        except Exception as e:
            return f"News search error: {str(e)}"

    def analyze_stock_with_ai(self, symbol: str, stock_data: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Ollama AI (qwen2.5:7b) to analyze stock and provide BUY/SELL recommendation.
        """
        try:
            # Prepare context for AI
            current_price = stock_data.get("current_price", "N/A")
            prev_close = stock_data.get("prev_close", "N/A")
            price_change_pct = stock_data.get("price_change_pct", 0)
            volume = stock_data.get("volume", "N/A")
            high_5d = stock_data.get("high_5d", "N/A")
            low_5d = stock_data.get("low_5d", "N/A")
            sma_5 = indicators.get("sma_5", "N/A")
            sma_20 = indicators.get("sma_20", "N/A")
            rsi = indicators.get("rsi", "N/A")
            momentum_5d = indicators.get("momentum_5d", 0)

            news = self.search_tavily(symbol)

            prompt = f"""Analyze the stock {symbol} based on the following data and provide a trading recommendation:

**Stock Data:**
- Current Price: ${current_price}
- Previous Close: ${prev_close}
- Price Change: {price_change_pct:.2f}%
- Volume: {volume}
- 5-Day High: ${high_5d}
- 5-Day Low: ${low_5d}
- 5-Day Momentum: {momentum_5d}

**Technical Indicators:**
- SMA 5: ${sma_5}
- SMA 20: ${sma_20}
- RSI: {rsi}

**Recent Market News/Analysis:**
{news}

Based on this data, provide your analysis in the following JSON format:
{{
  "recommendation": "BUY" or "SELL" or "HOLD",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "target_price": <number or null>,
  "reasoning": "<brief explanation of the recommendation>"
}}

Respond ONLY with valid JSON, no additional text."""

            response_text = self.query_ollama(prompt)

            # Try to parse JSON response
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {
                        "recommendation": "HOLD",
                        "confidence": "LOW",
                        "target_price": current_price,
                        "reasoning": f"AI response parsing error. Raw: {response_text[:100]}"
                    }

            return {
                "symbol": symbol,
                "recommendation": analysis.get("recommendation", "HOLD"),
                "confidence": analysis.get("confidence", "LOW"),
                "target_price": analysis.get("target_price"),
                "reasoning": analysis.get("reasoning", ""),
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "recommendation": "HOLD",
                "confidence": "LOW",
                "target_price": stock_data.get("current_price"),
                "reasoning": f"AI analysis error: {str(e)}"
            }

    def send_whatsapp_message(self, message: str) -> bool:
        """
        Send WhatsApp message using Twilio API.
        """
        if not self.enable_whatsapp_send:
            print(f"[{self._now_str()}] WhatsApp sending disabled. Message would be: {message[:100]}")
            return False

        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_whatsapp_from]):
            print(f"[{self._now_str()}] Twilio credentials missing. Cannot send WhatsApp.")
            return False

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
            
            auth = (self.twilio_account_sid, self.twilio_auth_token)
            data = {
                "From": self.twilio_whatsapp_from,
                "To": f"whatsapp:+{self.whatsapp_number}",
                "Body": message,
            }

            response = requests.post(url, auth=auth, data=data, timeout=self.request_timeout)
            response.raise_for_status()
            
            print(f"[{self._now_str()}] WhatsApp message sent successfully")
            return True
        except Exception as e:
            print(f"[{self._now_str()}] WhatsApp send error: {str(e)}")
            return False

    def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Perform complete analysis of a single stock.
        """
        print(f"[{self._now_str()}] Analyzing {symbol}...")

        # Get stock data
        stock_data = self.get_stock_data(symbol)
        if "error" in stock_data:
            print(f"[{self._now_str()}] Error fetching data for {symbol}: {stock_data.get('error')}")
            return stock_data

        # Calculate technical indicators
        indicators = self.calculate_technical_indicators(stock_data)
        
        # Get AI recommendation
        analysis = self.analyze_stock_with_ai(symbol, stock_data, indicators)

        # Combine results
        result = {
            "symbol": symbol,
            "timestamp": self._now_str(),
            "stock_data": stock_data,
            "indicators": indicators,
            "analysis": analysis,
        }

        return result

    def run_analysis_all_stocks(self) -> List[Dict[str, Any]]:
        """
        Analyze all stocks and send summary report.
        """
        print(f"\n{'='*60}")
        print(f"[{self._now_str()}] Starting stock analysis for {len(self.stocks)} symbols")
        print(f"{'='*60}\n")

        self.analysis_results = []
        buy_recommendations = []
        sell_recommendations = []

        for symbol in self.stocks:
            result = self.analyze_stock(symbol)
            self.analysis_results.append(result)

            # Track recommendations
            if "analysis" in result:
                recommendation = result["analysis"].get("recommendation", "HOLD")
                if recommendation == "BUY":
                    buy_recommendations.append(symbol)
                elif recommendation == "SELL":
                    sell_recommendations.append(symbol)

            # Respect rate limiting
            time.sleep(self.symbol_pause_seconds)

        # Generate and send report
        self._send_analysis_report(buy_recommendations, sell_recommendations)

        return self.analysis_results

    def _send_analysis_report(self, buys: List[str], sells: List[str]) -> None:
        """
        Send comprehensive analysis report via WhatsApp.
        """
        report = f"""📊 STOCK ANALYSIS REPORT
{self._now_str()}

🟢 BUY SIGNALS: {len(buys)}
{', '.join(buys) if buys else 'None'}

🔴 SELL SIGNALS: {len(sells)}
{', '.join(sells) if sells else 'None'}

⏸️ HOLD: {len(self.stocks) - len(buys) - len(sells)}

Powered by Ollama (qwen2.5:7b)"""

        print(f"\n{report}\n")
        self.send_whatsapp_message(report)

        # Send detailed results for BUY signals
        for result in self.analysis_results:
            if result.get("analysis", {}).get("recommendation") == "BUY":
                symbol = result.get("symbol")
                stock_data = result.get("stock_data", {})
                analysis = result.get("analysis", {})

                detail_msg = f"""✅ BUY SIGNAL: {symbol}
Price: ${stock_data.get('current_price', 'N/A')}
Target: ${analysis.get('target_price', 'N/A')}
Confidence: {analysis.get('confidence', 'N/A')}
Reason: {analysis.get('reasoning', 'N/A')[:200]}"""

                print(detail_msg)
                self.send_whatsapp_message(detail_msg)
    def schedule_hourly(self) -> None:
        """
        Schedule stock analysis to run every hour.
        Requires 'schedule' package: pip install schedule
        """
        if schedule is None:
            print("ERROR: 'schedule' package not installed. Install with: pip install schedule")
            return

        def job():
            try:
                self.run_analysis_all_stocks()
            except Exception as e:
                print(f"[{self._now_str()}] Scheduled job error: {str(e)}")

        # Schedule the job to run every hour
        schedule.every().hour.do(job)
        
        print(f"[{self._now_str()}] Stock analysis scheduled to run every hour")
        print(f"[{self._now_str()}] Starting scheduler... Press Ctrl+C to exit\n")

        # Keep scheduler running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print(f"\n[{self._now_str()}] Scheduler stopped by user")


if __name__ == "__main__":
    import sys
    
    agent = StockAnalysisAgent()
    print(f"Stock Analysis Agent initialized with {len(agent.stocks)} stocks")
    print(f"Configuration:")
    print(f"  - Ollama Host: {agent.ollama_host}")
    print(f"  - Ollama Model: {agent.ollama_model}")
    print(f"  - WhatsApp Enabled: {agent.enable_whatsapp_send}")
    print(f"  - WhatsApp Number: +{agent.whatsapp_number}")
    print(f"  - Tavily API: {'Configured' if agent.tavily_api_key else 'Not configured'}\n")

    if len(sys.argv) > 1 and sys.argv[1] == "schedule":
        # Run scheduler
        agent.schedule_hourly()
    else:
        # Run once
        results = agent.run_analysis_all_stocks()
        print(f"\n{'='*60}")
        print(f"[{agent._now_str()}] Analysis complete. {len(results)} stocks analyzed.")
        print(f"{'='*60}")
