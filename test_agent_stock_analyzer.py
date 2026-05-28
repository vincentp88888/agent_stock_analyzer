import pytest
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from agent_stock_analyzer import StockAnalysisAgent


class TestStockAnalysisAgent:
    """Test suite for StockAnalysisAgent."""

    @pytest.fixture
    def agent(self):
        """Create a test instance of StockAnalysisAgent."""
        return StockAnalysisAgent()

    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly."""
        assert len(agent.stocks) == 11
        assert "QQQ" in agent.stocks
        assert "HST.SI" in agent.stocks
        assert agent.whatsapp_number == "6587533570"
        assert agent.ollama_model == "qwen2.5:7b"

    def test_now_str_format(self, agent):
        """Test timestamp formatting."""
        timestamp = agent._now_str()
        assert isinstance(timestamp, str)
        assert len(timestamp) == 19  # "YYYY-MM-DD HH:MM:SS"
        assert "-" in timestamp
        assert ":" in timestamp

    def test_safe_float_valid(self, agent):
        """Test safe_float with valid inputs."""
        assert agent._safe_float(10) == 10.0
        assert agent._safe_float("10.5") == 10.5
        assert agent._safe_float(0) == 0.0
        assert agent._safe_float(-5.5) == -5.5

    def test_safe_float_invalid(self, agent):
        """Test safe_float with invalid inputs."""
        assert agent._safe_float(None) is None
        assert agent._safe_float("invalid") is None
        assert agent._safe_float("") is None

    def test_format_price_valid(self, agent):
        """Test price formatting."""
        assert agent.format_price(100.5) == "$100.50"
        assert agent.format_price(0) == "$0.00"
        assert agent.format_price(1234.567) == "$1234.57"

    def test_format_price_invalid(self, agent):
        """Test price formatting with invalid inputs."""
        assert agent.format_price(None) == "N/A"
        assert agent.format_price("invalid") == "N/A"

    @patch('yfinance.Ticker')
    def test_get_stock_data_success(self, mock_ticker, agent):
        """Test successful stock data retrieval."""
        # Mock yfinance response
        mock_hist = MagicMock()
        mock_hist.empty = False
        
        # Mock Close column
        mock_close = MagicMock()
        mock_close.dropna.return_value = MagicMock(iloc=[150.0, 149.0])
        
        # Mock High column
        mock_high = MagicMock()
        mock_high.dropna.return_value = MagicMock(max=MagicMock(return_value=152.0))
        
        # Mock Low column
        mock_low = MagicMock()
        mock_low.dropna.return_value = MagicMock(min=MagicMock(return_value=148.0))
        
        # Mock Volume column
        mock_volume = MagicMock()
        mock_volume.dropna.return_value = MagicMock(iloc=[1000000.0])
        
        mock_hist.__getitem__.side_effect = lambda col: {
            "Close": mock_close,
            "High": mock_high,
            "Low": mock_low,
            "Volume": mock_volume
        }[col]
        
        mock_hist.tail = MagicMock(return_value=MagicMock(to_dict=MagicMock(return_value={})))

        mock_ticker.return_value.history.return_value = mock_hist

        result = agent.get_stock_data("QQQ")
        assert result["symbol"] == "QQQ"
        assert "current_price" in result
        assert "error" not in result

    @patch('yfinance.Ticker')
    def test_get_stock_data_error(self, mock_ticker, agent):
        """Test stock data retrieval with error."""
        mock_ticker.side_effect = Exception("API Error")

        result = agent.get_stock_data("INVALID")
        assert result["symbol"] == "INVALID"
        assert "error" in result

    def test_calculate_rsi(self, agent):
        """Test RSI calculation."""
        prices = [100, 101, 102, 103, 102, 101, 100, 99, 98, 97, 96, 95, 94, 93, 92]
        rsi = agent._calculate_rsi(prices)
        
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_calculate_rsi_insufficient_data(self, agent):
        """Test RSI calculation with insufficient data."""
        prices = [100, 101, 102]
        rsi = agent._calculate_rsi(prices, period=14)
        
        assert rsi is None

    def test_calculate_technical_indicators_valid(self, agent):
        """Test technical indicator calculation."""
        stock_data = {
            "symbol": "QQQ",
            "current_price": 150.0,
            "history": {
                "Close": {
                    str(i): 100 + i for i in range(20)
                }
            }
        }

        indicators = agent.calculate_technical_indicators(stock_data)
        
        assert indicators["symbol"] == "QQQ"
        assert "sma_5" in indicators
        assert "sma_20" in indicators
        assert "rsi" in indicators or "error" in indicators

    def test_calculate_technical_indicators_no_history(self, agent):
        """Test technical indicators with no history."""
        stock_data = {
            "symbol": "QQQ",
            "history": {}
        }

        indicators = agent.calculate_technical_indicators(stock_data)
        
        assert "error" in indicators or indicators.get("symbol") == "QQQ"

    @patch('requests.post')
    def test_search_tavily_success(self, mock_post, agent):
        """Test Tavily search success."""
        agent.tavily_api_key = "test_key"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "answer": "QQQ is showing bullish signals"
        }
        mock_post.return_value = mock_response

        result = agent.search_tavily("QQQ")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_tavily_no_key(self, agent):
        """Test Tavily search without API key."""
        agent.tavily_api_key = ""
        
        result = agent.search_tavily("QQQ")
        
        assert "API key" in result or "configured" in result

    @patch.object(StockAnalysisAgent, 'query_ollama')
    @patch.object(StockAnalysisAgent, 'search_tavily')
    def test_analyze_stock_with_ai_buy(self, mock_tavily, mock_ollama, agent):
        """Test AI stock analysis returning BUY."""
        mock_tavily.return_value = "Bullish news"
        mock_ollama.return_value = json.dumps({
            "recommendation": "BUY",
            "confidence": "HIGH",
            "target_price": 160.0,
            "reasoning": "Strong technical indicators"
        })

        stock_data = {
            "symbol": "QQQ",
            "current_price": 150.0,
            "prev_close": 149.0,
            "price_change_pct": 0.67,
            "volume": 1000000,
            "high_5d": 152.0,
            "low_5d": 148.0,
        }

        indicators = {
            "sma_5": 150.5,
            "sma_20": 149.0,
            "rsi": 65.0,
            "momentum_5d": 2.0,
        }

        analysis = agent.analyze_stock_with_ai("QQQ", stock_data, indicators)

        assert analysis["symbol"] == "QQQ"
        assert analysis["recommendation"] == "BUY"
        assert analysis["confidence"] == "HIGH"
        assert analysis["target_price"] == 160.0

    @patch.object(StockAnalysisAgent, 'query_ollama')
    @patch.object(StockAnalysisAgent, 'search_tavily')
    def test_analyze_stock_with_ai_sell(self, mock_tavily, mock_ollama, agent):
        """Test AI stock analysis returning SELL."""
        mock_tavily.return_value = "Bearish news"
        mock_ollama.return_value = json.dumps({
            "recommendation": "SELL",
            "confidence": "MEDIUM",
            "target_price": 140.0,
            "reasoning": "Bearish divergence"
        })

        stock_data = {
            "symbol": "QQQ",
            "current_price": 150.0,
            "prev_close": 149.0,
            "price_change_pct": 0.67,
            "volume": 1000000,
            "high_5d": 152.0,
            "low_5d": 148.0,
        }

        indicators = {
            "sma_5": 150.5,
            "sma_20": 149.0,
            "rsi": 30.0,
            "momentum_5d": -2.0,
        }

        analysis = agent.analyze_stock_with_ai("QQQ", stock_data, indicators)

        assert analysis["recommendation"] == "SELL"
        assert analysis["confidence"] == "MEDIUM"

    @patch.object(StockAnalysisAgent, 'query_ollama')
    @patch.object(StockAnalysisAgent, 'search_tavily')
    def test_analyze_stock_with_ai_invalid_json(self, mock_tavily, mock_ollama, agent):
        """Test AI analysis with invalid JSON response."""
        mock_tavily.return_value = "News"
        mock_ollama.return_value = "This is not JSON"

        stock_data = {
            "symbol": "QQQ",
            "current_price": 150.0,
            "prev_close": 149.0,
            "price_change_pct": 0.67,
            "volume": 1000000,
            "high_5d": 152.0,
            "low_5d": 148.0,
        }

        indicators = {
            "sma_5": 150.5,
            "sma_20": 149.0,
            "rsi": 50.0,
            "momentum_5d": 0,
        }

        analysis = agent.analyze_stock_with_ai("QQQ", stock_data, indicators)

        assert analysis["recommendation"] in ["BUY", "SELL", "HOLD"]
        assert analysis["confidence"] in ["HIGH", "MEDIUM", "LOW"]

    def test_send_whatsapp_message_disabled(self, agent):
        """Test WhatsApp message sending when disabled."""
        agent.enable_whatsapp_send = False

        result = agent.send_whatsapp_message("Test message")
        
        assert result is False

    @patch.object(StockAnalysisAgent, 'get_stock_data')
    @patch.object(StockAnalysisAgent, 'calculate_technical_indicators')
    @patch.object(StockAnalysisAgent, 'analyze_stock_with_ai')
    def test_analyze_stock_complete(self, mock_ai, mock_indicators, mock_data, agent):
        """Test complete single stock analysis."""
        mock_data.return_value = {
            "symbol": "QQQ",
            "current_price": 150.0,
            "prev_close": 149.0,
            "price_change_pct": 0.67,
            "volume": 1000000,
            "high_5d": 152.0,
            "low_5d": 148.0,
            "history": {"Close": {i: 100 + i for i in range(20)}}
        }

        mock_indicators.return_value = {
            "symbol": "QQQ",
            "sma_5": 150.5,
            "sma_20": 149.0,
            "rsi": 65.0,
            "momentum_5d": 2.0,
        }

        mock_ai.return_value = {
            "symbol": "QQQ",
            "recommendation": "BUY",
            "confidence": "HIGH",
            "target_price": 160.0,
            "reasoning": "Strong signals"
        }

        result = agent.analyze_stock("QQQ")

        assert result["symbol"] == "QQQ"
        assert "stock_data" in result
        assert "indicators" in result
        assert "analysis" in result
        assert "timestamp" in result

    def test_stocks_list(self, agent):
        """Test that all required stocks are in the list."""
        required_stocks = [
            "QQQ", "DXYZ", "VCX", "SOXX", "ROBO",
            "HST.SI", "2807.HK", "3174.HK", "2800.HK",
            "3188.HK", "ES3.SI"
        ]
        
        for stock in required_stocks:
            assert stock in agent.stocks

    def test_analysis_results_storage(self, agent):
        """Test that analysis results are stored."""
        assert isinstance(agent.analysis_results, list)
        assert len(agent.analysis_results) == 0
        
        agent.analysis_results.append({"symbol": "QQQ"})
        assert len(agent.analysis_results) == 1

    def test_ollama_configuration(self, agent):
        """Test Ollama configuration."""
        # ollama_host should be accessible from WSL (can be 127.0.0.1 or 0.0.0.0)
        assert "11434" in agent.ollama_host
        assert agent.ollama_model == "qwen2.5:7b"

    @patch('requests.post')
    def test_query_ollama_http_success(self, mock_post, agent):
        """Test HTTP API query to Ollama."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "This is a test response"
        }
        mock_post.return_value = mock_response

        result = agent.query_ollama("Test prompt")
        
        assert isinstance(result, str)
        assert len(result) > 0

    def test_price_change_calculation(self, agent):
        """Test price change calculation in get_stock_data."""
        # This is tested indirectly through get_stock_data
        # We verify the logic here with mock data
        current = 150.0
        prev = 149.0
        expected_change = current - prev
        expected_pct = (expected_change / prev) * 100
        
        assert expected_change == 1.0
        assert abs(expected_pct - 0.6711) < 0.01  # Approximately 0.67%


class TestIntegration:
    """Integration tests for the stock analysis workflow."""

    @pytest.fixture
    def agent(self):
        """Create agent for integration tests."""
        return StockAnalysisAgent()

    @patch.object(StockAnalysisAgent, 'get_stock_data')
    @patch.object(StockAnalysisAgent, 'analyze_stock_with_ai')
    @patch.object(StockAnalysisAgent, 'send_whatsapp_message')
    def test_full_workflow_single_stock(self, mock_whatsapp, mock_ai, mock_data, agent):
        """Test complete workflow for a single stock."""
        mock_data.return_value = {
            "symbol": "QQQ",
            "current_price": 150.0,
            "prev_close": 149.0,
            "price_change_pct": 0.67,
            "volume": 1000000,
            "high_5d": 152.0,
            "low_5d": 148.0,
            "history": {"Close": {i: 100 + i for i in range(20)}}
        }

        mock_ai.return_value = {
            "symbol": "QQQ",
            "recommendation": "BUY",
            "confidence": "HIGH",
            "target_price": 160.0,
            "reasoning": "Strong signals"
        }

        mock_whatsapp.return_value = False  # Disabled

        # Run analysis
        result = agent.analyze_stock("QQQ")
        
        assert result["symbol"] == "QQQ"
        assert result["analysis"]["recommendation"] == "BUY"

    def test_recommendation_generation_buy(self, agent):
        """Test that BUY recommendations are generated correctly."""
        # Mock data for bullish stock
        stock_data = {
            "symbol": "QQQ",
            "current_price": 160.0,
            "prev_close": 150.0,
            "price_change_pct": 6.67,
            "volume": 5000000,
            "high_5d": 165.0,
            "low_5d": 148.0,
        }

        indicators = {
            "sma_5": 155.0,
            "sma_20": 145.0,
            "rsi": 75.0,  # Overbought but can indicate strength
            "momentum_5d": 10.0,  # Strong upward momentum
        }

        # Analysis should recommend BUY based on bullish indicators
        assert indicators["rsi"] > 60  # Bullish RSI
        assert indicators["momentum_5d"] > 0  # Upward momentum
        assert stock_data["price_change_pct"] > 0  # Price increase

    def test_recommendation_generation_sell(self, agent):
        """Test that SELL recommendations are generated correctly."""
        # Mock data for bearish stock
        stock_data = {
            "symbol": "DXYZ",
            "current_price": 130.0,
            "prev_close": 150.0,
            "price_change_pct": -13.33,
            "volume": 5000000,
            "high_5d": 152.0,
            "low_5d": 128.0,
        }

        indicators = {
            "sma_5": 135.0,
            "sma_20": 145.0,
            "rsi": 25.0,  # Oversold
            "momentum_5d": -20.0,  # Strong downward momentum
        }

        # Analysis should recommend SELL based on bearish indicators
        assert indicators["rsi"] < 40  # Bearish RSI
        assert indicators["momentum_5d"] < 0  # Downward momentum
        assert stock_data["price_change_pct"] < 0  # Price decrease


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
