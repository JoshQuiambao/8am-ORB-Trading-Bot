# 8am-ORB-Trading-Bot
Automated 8AM Opening Range Breakout strategy
[README.md](https://github.com/user-attachments/files/26320471/README.md)
# 🦍 Yeshua's 8AM ORB Trading Bot

> Automated Opening Range Breakout strategy for MES futures — built in Python with Rithmic API, auto trade logging, and Telegram alerts.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Status](https://img.shields.io/badge/Status-In%20Development-yellow?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Rithmic-orange?style=flat-square)

---

## What This Is

A fully automated futures trading bot that executes the **8AM Opening Range Breakout (ORB)** setup on the Micro E-mini S&P 500 (MES). Built from scratch by a funded futures trader who wanted to systematize a manually proven edge.

The bot watches every price tick from 8:00 AM EST, locks the opening range at 8:15 AM, and fires a bracket order the moment price breaks out with confirmation. One trade per session. Disciplined. Automated. No emotions.

---

## How It Works

```
8:00 AM EST   →   Bot activates. Watches every tick.
8:00–8:15 AM  →   ORB Range builds. Tracks high and low.
8:15 AM       →   Range LOCKS. High and low are set.
8:15–11:00 AM →   Bot watches for breakout.
Breakout!     →   Bracket order fires instantly.
                  Entry + Stop Loss + Take Profit placed simultaneously.
11:00 AM      →   Trading window closes. Position flattened if still open.
End of Day    →   Trade logged to CSV. Telegram summary sent.
```

---

## Architecture

The strategy is split into five clean modules:

```
trading_bot/
├── orb_strategy.py      # Main engine — ties everything together
├── notifications.py     # Auto journal (CSV) + Telegram alerts
├── test_strategy.py     # Full simulation test — no real money needed
└── venv/                # Python virtual environment
```

### Core Classes

| Class | File | Purpose |
|---|---|---|
| `ORBRange` | `orb_strategy.py` | Builds and locks the 8AM opening range |
| `RiskManager` | `orb_strategy.py` | Tracks daily P&L, enforces loss limits |
| `OrderExecutor` | `orb_strategy.py` | Connects to Rithmic and fires bracket orders |
| `ORBStrategy` | `orb_strategy.py` | Main engine — processes every price tick |
| `AutoJournal` | `notifications.py` | Writes every trade to CSV automatically |
| `TelegramNotifier` | `notifications.py` | Sends real time alerts to your phone |

---

## Strategy Configuration

All settings are controlled from one `CONFIG` block at the top of `orb_strategy.py`. No digging through code to change parameters.

```python
CONFIG = {
    "symbol":           "MESM6",      # MES June contract
    "exchange":         "CME",
    "timezone":         "US/Eastern",

    # ORB Time Window
    "orb_start":        time(8, 0),   # 8:00 AM EST
    "orb_end":          time(8, 15),  # 8:15 AM EST

    # Trading Window
    "trade_start":      time(8, 15),
    "trade_end":        time(11, 0),  # Stop trading at 11 AM

    # Risk Management
    "contracts":        2,            # Number of contracts
    "stop_ticks":       60,           # 15 points = 60 ticks
    "target_ticks":     92,           # 23 points = 92 ticks
    "max_daily_loss":   350,          # Bot shuts down if down $350

    # Breakout confirmation
    "breakout_buffer":  0.25,         # Price must close 1 tick past ORB
}
```

---

## Risk Management

Risk management is **hardcoded into the bot** — not optional, not bypassable.

- **Daily loss limit** — bot automatically shuts down when hit. No override.
- **One trade per session** — once a breakout fires, no more trades that day.
- **Trading hours enforced** — bot ignores price action outside 8:15–11:00 AM.
- **Bracket orders** — stop loss and take profit placed simultaneously with entry. Never naked.
- **11 AM flat** — any open position is force closed at end of trading window.

```
Stop Loss  : 15 points = $150 per trade (2 contracts)
Take Profit: 23 points = $230 per trade (2 contracts)
R:R Ratio  : 1:1.53
Max Daily  : $350
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.11 | Core language |
| async_rithmic | Rithmic API connection — market data and order execution |
| asyncio | Async event loop for real time tick processing |
| pandas | Trade data handling and analysis |
| aiohttp | Async HTTP for Telegram notifications |
| pytz | Timezone handling for session management |

---

## Setup

### Prerequisites

- Python 3.11+
- Rithmic account with API access
- Linux or macOS (built and tested on Chromebook Linux environment)

### Installation

```bash
# Clone the repo
git clone https://github.com/JoshQuiambao/trading-bot.git
cd trading-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install async-rithmic pandas numpy aiohttp pytz
```

### Configuration

Add your Rithmic credentials to the `run()` method in `orb_strategy.py`:

```python
client = RithmicClient(
    user        = "YOUR_RITHMIC_USERNAME",
    password    = "YOUR_RITHMIC_PASSWORD",
    system_name = "YOUR_SYSTEM_NAME",
    app_name    = "YeshuaORBStrategy",
    app_version = "1.0",
    url         = "YOUR_RITHMIC_SERVER_URL",
)
```

> Never commit credentials to GitHub. Use environment variables in production.

### Run Simulation Test (No Real Money)

```bash
python3 test_strategy.py
```

Expected output:
```
════════════════════════════════════
🧪 RUNNING STRATEGY SIMULATION TEST
════════════════════════════════════

TEST 1: Building ORB Range (8:00-8:15 AM)
ORB High    : 6660.0
ORB Low     : 6642.75
ORB Range   : 17.25 points
ORB Locked  : True

TEST 2: Checking for Breakout
No breakout at 6655.0 — waiting...
No breakout at 6658.0 — waiting...
✅ Breakout detected: LONG at 6661.0

TEST 3: Calculate Stop & Target Levels
Entry Price  : 6661.0
Stop Loss    : 6646.0  (60 ticks = $150.00)
Take Profit  : 6668.75 (92 ticks = $230.00)
R:R Ratio    : 1:1.0

TEST 4: P&L Calculation
If TP hits   : +$230.0  WIN 🟢
If SL hits   : -$150.0  LOSS 🔴

✅ ALL TESTS PASSED — Strategy Ready!
════════════════════════════════════
```

### Run Live

```bash
python3 orb_strategy.py
```

---

## Telegram Notifications

The bot sends real time alerts to your phone for every major event:

| Alert | Trigger |
|---|---|
| 🔒 ORB Locked | 8:15 AM — range is set |
| 🟢 Long Entry | Breakout above ORB high |
| 🔴 Short Entry | Breakout below ORB low |
| ✅ Trade Closed | TP or SL hit |
| 🛑 Bot Shutdown | Daily loss limit hit |
| 📊 Daily Summary | End of session recap |

Setup: Create a bot via [@BotFather](https://t.me/botfather) on Telegram and add your token and chat ID to `notifications.py`.

---

## Auto Trade Journal

Every trade is automatically logged to `trade_log.csv` with the following columns:

```
Date, Time, Instrument, Direction, Setup, Entry Price, Stop Loss,
Take Profit, Exit Price, Contracts, Tick Value, Point Value,
Gross P&L, Fees, Net P&L, Result, R-Multiple, Exit Reason, Notes
```

The CSV is fully compatible with Google Sheets for performance analysis.

---

## Sample Strategy Output

```
════════════════════════════════════════
🚀 Yeshua's 8AM ORB STRATEGY STARTING
   Symbol     : MESM6
   ORB Window : 08:00:00 - 08:15:00
   Trade Hours: 08:15:00 - 11:00:00
   Stop       : 60 ticks
   Target     : 92 ticks
   Max Loss   : $350
════════════════════════════════════════

✅ Connected to Rithmic
📡 Subscribed to MESM6 price feed
⏳ Waiting for 8:00 AM ORB window...

ORB High updated: 6660.25
ORB Low updated: 6642.75
✅ ORB LOCKED — High: 6660.25 | Low: 6642.75 | Range: 17.5 points

🟢 LONG BREAKOUT CONFIRMED at 6660.50
📐 Entry: 6660.50 | Stop: 6645.50 | Target: 6683.25
🚀 BRACKET ORDER PLACED SUCCESSFULLY

✅ TRADE CLOSED — WIN
Net P&L: +$221.00
════════════════════════════════════════
📊 END OF DAY SUMMARY
Total Trades  : 1
Daily P&L     : $221.00
Status        : ✅ Active
════════════════════════════════════════
```

---

## Roadmap

- [x] ORB range builder
- [x] Breakout detection with confirmation buffer
- [x] Bracket order execution via Rithmic API
- [x] Auto trade journal (CSV)
- [x] Telegram real time alerts
- [x] Daily loss limit protection
- [ ] Live Rithmic connection (pending API approval)
- [ ] Backtesting module
- [ ] Multi-instrument support (MNQ, MGC)
- [ ] Web dashboard for live monitoring
- [ ] Tradovate API version

---

## Disclaimer

This project is for educational purposes only. Trading futures involves substantial risk of loss. Past performance is not indicative of future results. This is not financial advice.

---

## About the Author

Funded futures trader across Lucid Trading, TopStep, and Tradeify. Former process engineer at Salesforce. Trading GC, ES, NQ and their micros from South Beach, Miami.

- 🌐 [toptickgorilla.com](https://toptickgorilla.com)
- 📸 [@toptickgorilla](https://instagram.com/toptickgorilla)
- 🐦 [@bandypelosi](https://twitter.com/bandypelosi)

---

*Built by a trader, for traders. Not financial advice.*
