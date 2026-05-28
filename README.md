# Stock Analysis Agent - AI-Powered Trading Recommendations

An intelligent stock analysis agent that uses **Ollama (qwen2.5:7b)** AI model to generate **BUY/SELL/HOLD** recommendations for 11 major stock symbols and sends recommendations via **WhatsApp** using Twilio.

## Features

✨ **Key Capabilities:**
- 🤖 AI-powered analysis using Ollama (qwen2.5:7b)
- 📊 Technical indicator calculations (SMA, RSI, momentum)
- 🔍 Market news integration via Tavily API
- 💬 WhatsApp notifications via Twilio
- ⏰ Hourly scheduled analysis
- 🧪 Comprehensive test suite (27 tests, all passing)
- 🌍 Multi-market support (US, Singapore, Hong Kong stocks)

## Monitored Stocks

- **US Markets**: QQQ, DXYZ, VCX, SOXX, ROBO
- **Singapore**: HST.SI, ES3.SI
- **Hong Kong**: 2807.HK, 3174.HK, 2800.HK, 3188.HK

## Environment Setup

### Prerequisites

1. **Windows 11 with Ollama installed**
   - Download from: https://ollama.ai
   - Model: qwen2.5:7b (7B parameter model)
   - Runs on: http://127.0.0.1:11434

2. **WSL Ubuntu 26.04 LTS** (Optional, for remote execution)
   - Python 3.14.4
   - Can access Ollama via 127.0.0.1:11434

3. **Python 3.13+** (Windows or WSL)
   - Required packages in requirements.txt

### Installation

```bash
# Clone/setup the project
cd c:\Users\itpan\agent_stock_analyzer

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
```

### Configuration (`.env` file)

```env
# Ollama Configuration
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b

# Twilio WhatsApp Setup (get from https://www.twilio.com/console)
TWILIO_ACCOUNT_SID=your_sid_here
TWILIO_AUTH_TOKEN=your_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# WhatsApp Recipient
WHATSAPP_NUMBER=6587533570
ENABLE_WHATSAPP_SEND=false  # Set to 'true' to enable

# Tavily API for news (optional, from https://www.tavily.com/)
TAVILY_API_KEY=your_api_key_here

# Timing
REQUEST_TIMEOUT_SECONDS=30
SYMBOL_PAUSE_SECONDS=3
MAX_TAVILY_RESULTS=3
```

## Usage

### Run Once (One-shot analysis)

```bash
python agent_stock_analyzer.py
```

Output:
```
Stock Analysis Agent initialized with 11 stocks
Configuration:
  - Ollama Host: http://127.0.0.1:11434
  - Ollama Model: qwen2.5:7b
  - WhatsApp Enabled: False
  - WhatsApp Number: +6587533570
  - Tavily API: Not configured

============================================================
[2026-05-28 14:30:45] Starting stock analysis for 11 symbols
============================================================

[2026-05-28 14:30:45] Analyzing QQQ...
[2026-05-28 14:30:48] Analyzing DXYZ...
...
```

### Run Every Hour (Scheduler)

```bash
python agent_stock_analyzer.py schedule
```

Or use the dedicated scheduler:

```bash
python scheduler.py
```

### Demo with Mock Data

See how the analysis works without live data:

```bash
python demo.py
```

## Analysis Output

### Stock Analysis Report

The agent analyzes each stock and generates:

1. **Price Data**
   - Current price
   - Previous close
   - Price change (%)
   - Volume
   - 5-day high/low

2. **Technical Indicators**
   - Simple Moving Average (SMA 5, SMA 20)
   - Relative Strength Index (RSI)
   - 5-day momentum

3. **AI Analysis** (via Ollama)
   - **Recommendation**: BUY | SELL | HOLD
   - **Confidence**: HIGH | MEDIUM | LOW
   - **Target Price**: Expected price target
   - **Reasoning**: Technical and fundamental analysis

### WhatsApp Notifications

When enabled, the agent sends:

1. **Summary Report**
   ```
   📊 STOCK ANALYSIS REPORT
   2026-05-28 14:35:22

   🟢 BUY SIGNALS: 3
   QQQ, SOXX, ROBO

   🔴 SELL SIGNALS: 2
   DXYZ, VCX

   ⏸️ HOLD: 6

   Powered by Ollama (qwen2.5:7b)
   ```

2. **Detailed Buy Signals** (one message per BUY)
   ```
   ✅ BUY SIGNAL: QQQ
   Price: $380.50
   Target: $400.00
   Confidence: HIGH
   Reason: Strong uptrend with bullish technical setup...
   ```

## Testing

### Run All Tests

```bash
pytest test_agent_stock_analyzer.py -v
```

### Test Results

```
============================= test session starts =============================
collected 27 items

test_agent_stock_analyzer.py::TestStockAnalysisAgent::test_agent_initialization PASSED
test_agent_stock_analyzer.py::TestStockAnalysisAgent::test_safe_float_valid PASSED
test_agent_stock_analyzer.py::TestStockAnalysisAgent::test_format_price_valid PASSED
test_agent_stock_analyzer.py::TestStockAnalysisAgent::test_get_stock_data_success PASSED
test_agent_stock_analyzer.py::TestStockAnalysisAgent::test_analyze_stock_with_ai_buy PASSED
test_agent_stock_analyzer.py::TestStockAnalysisAgent::test_analyze_stock_with_ai_sell PASSED
...
============================= 27 passed in 1.28s ===============================
```

### Test Coverage

The test suite covers:

- ✅ Agent initialization and configuration
- ✅ Data fetching (yfinance integration)
- ✅ Technical indicator calculations
- ✅ AI analysis with mock Ollama responses
- ✅ BUY/SELL recommendation generation
- ✅ WhatsApp message handling
- ✅ Error handling and edge cases
- ✅ Full workflow integration
- ✅ 27 total tests, all passing

## Architecture

```
agent_stock_analyzer.py
├── StockAnalysisAgent class
│   ├── get_stock_data()              # Fetch from yfinance
│   ├── calculate_technical_indicators() # SMA, RSI, momentum
│   ├── search_tavily()                # Market news
│   ├── analyze_stock_with_ai()        # Ollama analysis
│   ├── send_whatsapp_message()        # Twilio integration
│   ├── analyze_stock()                # Complete analysis
│   ├── run_analysis_all_stocks()      # Batch processing
│   └── schedule_hourly()              # Scheduler
│
test_agent_stock_analyzer.py
├── TestStockAnalysisAgent            # 24 unit tests
└── TestIntegration                   # 3 integration tests

demo.py                               # Demo with mock data
scheduler.py                          # Hourly scheduler
```

## Data Flow

```
1. Fetch Stock Data
   └─ yfinance API
      └─ Current price, volume, history

2. Calculate Technical Indicators
   ├─ Simple Moving Averages (5, 20)
   ├─ RSI (Relative Strength Index)
   └─ Price momentum

3. Get Market Context
   └─ Tavily API search (if key provided)
      └─ Recent news about the stock

4. AI Analysis
   └─ Ollama (qwen2.5:7b)
      ├─ Receives: price data + indicators + news
      ├─ Processes: Technical & fundamental analysis
      └─ Returns: BUY/SELL/HOLD + reasoning

5. Generate Notifications
   ├─ Console output
   └─ WhatsApp (if enabled)
      └─ Twilio API

6. Schedule Next Run
   └─ Wait 1 hour for next analysis
```

## Technical Details

### AI Model: Ollama (qwen2.5:7b)

- **Model**: Qwen 2.5 7B parameters
- **Size**: ~7 billion parameters
- **Performance**: Fast inference on standard hardware
- **Capabilities**: Stock analysis, financial reasoning, recommendation generation
- **Runs on**: Windows 11 (accessible from WSL via 127.0.0.1:11434)

### Integration Points

| Component | Purpose | Configuration |
|-----------|---------|---|
| **yfinance** | Stock price data | Automatic |
| **Ollama** | AI analysis | OLLAMA_HOST, OLLAMA_MODEL |
| **Tavily API** | Market news | TAVILY_API_KEY (optional) |
| **Twilio** | WhatsApp delivery | TWILIO_ACCOUNT_SID, etc. |
| **Schedule** | Hourly execution | Automatic |
| **Pytest** | Testing | Mocked dependencies |

## Performance

- **Per-Stock Analysis**: ~3 seconds (Ollama inference + API calls)
- **Total Run Time**: ~35-40 seconds for 11 stocks (includes rate limiting)
- **Memory Usage**: ~200-300 MB (Python + Ollama connection)
- **Network**: Minimal (only stock data + API calls)

## Error Handling

The agent handles:

- ✅ Missing stock data
- ✅ Ollama connection failures (fallback to HOLD)
- ✅ Invalid API responses
- ✅ Network timeouts
- ✅ Malformed JSON from AI
- ✅ Missing Twilio credentials
- ✅ WhatsApp delivery failures

## Troubleshooting

### Ollama Not Responding

```
Error: Ollama HTTP error: Connection refused
```

**Solution**:
1. Ensure Ollama is running on Windows: `ollama serve`
2. Check host/port: `OLLAMA_HOST=http://127.0.0.1:11434`
3. Verify model: `ollama list` should show `qwen2.5:7b`

### Stock Data Not Available

```
$DXYZ: possibly delisted; No price data found
```

**Solution**:
1. Verify ticker symbol on Yahoo Finance
2. Some regional stocks may have data delays
3. Check internet connection

### WhatsApp Not Sending

1. Set `ENABLE_WHATSAPP_SEND=true` in `.env`
2. Add Twilio credentials (get from twilio.com/console)
3. Ensure number format: `6587533570` (no country code prefix)
4. Check Twilio account balance

### Tests Failing

Run with verbose output:
```bash
pytest test_agent_stock_analyzer.py -vv --tb=long
```

## Future Enhancements

- 📈 Portfolio-level analysis
- 📍 Real-time streaming prices
- 🔔 Custom alert thresholds
- 📧 Email notifications
- 💾 Historical tracking/database
- 📱 Web dashboard
- 🌐 Multi-language support

## Requirements

See [requirements.txt](requirements.txt):

```
yfinance==0.2.40          # Stock data
requests==2.31.0           # HTTP requests
schedule==1.2.0            # Job scheduling
pytest==8.2.0              # Testing framework
pytest-asyncio==0.23.0     # Async test support
pytest-mock==3.14.0        # Mocking utilities
python-dotenv==1.0.1       # Environment variables
pytest-cov==5.0.0          # Code coverage
```

## Support

For issues or questions:

1. Check `.env` configuration
2. Run tests: `pytest test_agent_stock_analyzer.py -v`
3. Review demo: `python demo.py`
4. Check Ollama status: `ollama ps`

## License

This project is for educational and personal trading use.

---

**Last Updated**: May 28, 2026
**Status**: Production Ready ✅
**Test Coverage**: 27/27 tests passing (100%)
