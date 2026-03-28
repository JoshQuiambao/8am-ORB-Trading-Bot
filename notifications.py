# ─────────────────────────────────────────────
# NOTIFICATIONS & AUTO JOURNAL
# Feature 1 — Writes every trade to CSV
# Feature 2 — Sends Telegram alerts to phone
# ─────────────────────────────────────────────

import csv
import os
import asyncio
import aiohttp
from datetime import datetime
import pytz

# ── Telegram Configuration ─────────────────────
# We'll fill these in after setting up your bot
TELEGRAM_CONFIG = {
    "bot_token"  : "8614341633:AAE---FHfvXy60fAOKnpSVD5eiepes52yUY",    # From @BotFather on Telegram
    "chat_id"    : "Jet_Orb_Bot",      # Your personal chat ID
    "enabled"    : True,               # Set to True after setup
}

# ── Journal Configuration ──────────────────────
JOURNAL_CONFIG = {
    "file_path"  : os.path.expanduser("~/trading_bot/trade_log.csv"),
    "timezone"   : "US/Eastern",
}

# ══════════════════════════════════════════════
# FEATURE 1 — AUTO TRADE JOURNAL
# Writes every trade to CSV automatically
# ══════════════════════════════════════════════

class AutoJournal:
    """
    Automatically logs every trade to a CSV file.
    Compatible with Google Sheets — just import it.
    Columns match your trading journal exactly.
    """

    def __init__(self):
        self.file_path = JOURNAL_CONFIG["file_path"]
        self.tz        = pytz.timezone(JOURNAL_CONFIG["timezone"])
        self._initialize_file()

    def _initialize_file(self):
        """
        Creates the CSV file with headers if it
        doesn't exist yet. Safe to call every time.
        """
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Date",
                    "Time",
                    "Instrument",
                    "Direction",
                    "Setup",
                    "Entry Price",
                    "Stop Loss",
                    "Take Profit",
                    "Exit Price",
                    "Contracts",
                    "Tick Value ($)",
                    "Point Value ($)",
                    "Gross P&L ($)",
                    "Fees ($)",
                    "Net P&L ($)",
                    "Result",
                    "R-Multiple",
                    "Exit Reason",
                    "Notes",
                ])
            print(f"📒 Trade journal created at: {self.file_path}")

    def log_trade(self,
                  direction    : str,
                  entry_price  : float,
                  exit_price   : float,
                  stop_price   : float,
                  target_price : float,
                  contracts    : int,
                  gross_pnl    : float,
                  exit_reason  : str,
                  instrument   : str = "MES",
                  fee_per_contract : float = 4.50):
        """
        Called after every trade closes.
        Writes one row to the CSV automatically.
        """
        now       = datetime.now(self.tz)
        tick_val  = 1.25     # MES tick value
        point_val = 5.00     # MES point value
        fees      = round(fee_per_contract * contracts * 2, 2)  # Round trip
        net_pnl   = round(gross_pnl - fees, 2)
        result    = "WIN" if net_pnl > 0 else "LOSS" if net_pnl < 0 else "BREAK EVEN"

        # Calculate R-Multiple
        risk = abs(entry_price - stop_price) * point_val / 0.25 * contracts
        r_multiple = round(net_pnl / risk, 2) if risk != 0 else 0

        row = [
            now.strftime("%Y-%m-%d"),          # Date
            now.strftime("%H:%M:%S"),          # Time
            instrument,                         # Instrument
            direction,                          # Direction
            "8AM ORB Breakout",                # Setup
            entry_price,                        # Entry Price
            stop_price,                         # Stop Loss
            target_price,                       # Take Profit
            exit_price,                         # Exit Price
            contracts,                          # Contracts
            tick_val,                           # Tick Value
            point_val,                          # Point Value
            gross_pnl,                          # Gross P&L
            fees,                               # Fees
            net_pnl,                            # Net P&L
            result,                             # Result
            r_multiple,                         # R-Multiple
            exit_reason,                        # Exit Reason
            "Auto logged by ORB bot",           # Notes
        ]

        with open(self.file_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        print(f"📒 Trade logged to journal: {result} | Net P&L: ${net_pnl}")
        return net_pnl, result, r_multiple


# ══════════════════════════════════════════════
# FEATURE 2 — TELEGRAM NOTIFICATIONS
# Sends alerts to your phone in real time
# ══════════════════════════════════════════════

class TelegramNotifier:
    """
    Sends real time trade alerts to your phone
    via Telegram. Setup takes 2 minutes.
    """

    def __init__(self):
        self.token   = TELEGRAM_CONFIG["bot_token"]
        self.chat_id = TELEGRAM_CONFIG["chat_id"]
        self.enabled = TELEGRAM_CONFIG["enabled"]
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send(self, message: str):
        """Sends a message to your Telegram."""
        if not self.enabled:
            print(f"📱 [TELEGRAM DISABLED] {message}")
            return

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id"    : self.chat_id,
            "text"       : message,
            "parse_mode" : "HTML",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        print(f"📱 Telegram sent successfully")
                    else:
                        print(f"📱 Telegram failed: {response.status}")
        except Exception as e:
            print(f"📱 Telegram error: {e}")

    async def alert_orb_locked(self, high: float, low: float, range_size: float):
        """Fires when the ORB range locks at 8:15 AM."""
        msg = (
            f"🔒 <b>ORB LOCKED — MES</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 High    : <b>{high}</b>\n"
            f"📉 Low     : <b>{low}</b>\n"
            f"📐 Range   : <b>{range_size} pts</b>\n"
            f"⏰ Time    : 8:15 AM EST\n"
            f"👀 Watching for breakout..."
        )
        await self.send(msg)

    async def alert_entry(self, direction: str, price: float,
                          stop: float, target: float, contracts: int):
        """Fires the moment a trade entry executes."""
        emoji  = "🟢" if direction == "LONG" else "🔴"
        risk   = abs(price - stop) * 5.00 * contracts
        reward = abs(target - price) * 5.00 * contracts

        msg = (
            f"{emoji} <b>{direction} ENTRY — MES</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🎯 Entry   : <b>{price}</b>\n"
            f"🛑 Stop    : <b>{stop}</b>\n"
            f"💰 Target  : <b>{target}</b>\n"
            f"📦 Size    : <b>{contracts} contract(s)</b>\n"
            f"⚠️ Risk    : <b>${risk:.2f}</b>\n"
            f"🏆 Reward  : <b>${reward:.2f}</b>\n"
            f"⚖️ R:R     : <b>1:{reward/risk:.1f}</b>"
        )
        await self.send(msg)

    async def alert_exit(self, direction: str, entry: float,
                         exit_price: float, net_pnl: float,
                         result: str, exit_reason: str):
        """Fires the moment a trade closes."""
        emoji = "✅" if net_pnl > 0 else "❌"

        msg = (
            f"{emoji} <b>TRADE CLOSED — {result}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📊 Direction : <b>{direction}</b>\n"
            f"🎯 Entry     : <b>{entry}</b>\n"
            f"🚪 Exit      : <b>{exit_price}</b>\n"
            f"💵 Net P&L   : <b>${net_pnl:.2f}</b>\n"
            f"📋 Reason    : <b>{exit_reason}</b>"
        )
        await self.send(msg)

    async def alert_shutdown(self, reason: str, daily_pnl: float):
        """Fires when the bot shuts down for the day."""
        emoji = "✅" if daily_pnl > 0 else "🛑"

        msg = (
            f"{emoji} <b>BOT SHUTDOWN</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📋 Reason    : <b>{reason}</b>\n"
            f"💵 Daily P&L : <b>${daily_pnl:.2f}</b>\n"
            f"🕐 Time      : bot offline for today"
        )
        await self.send(msg)

    async def alert_daily_summary(self, trades: int,
                                   daily_pnl: float, wins: int, losses: int):
        """End of day summary sent to your phone."""
        emoji = "📈" if daily_pnl > 0 else "📉"

        msg = (
            f"{emoji} <b>DAILY SUMMARY — MES ORB BOT</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📊 Trades    : <b>{trades}</b>\n"
            f"✅ Wins      : <b>{wins}</b>\n"
            f"❌ Losses    : <b>{losses}</b>\n"
            f"💵 Daily P&L : <b>${daily_pnl:.2f}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"See trade_log.csv for full details."
        )
        await self.send(msg)