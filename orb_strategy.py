# ─────────────────────────────────────────────
# Yeshua's 8AM ORB STRATEGY — MES / Lucid Trading
# Built with async_rithmic + Rithmic API
# ─────────────────────────────────────────────
#Python commands: source ~/trading_bot/venv/bin/activate
# python3 test_strategy.py

import asyncio
import logging
from datetime import datetime, time
import pytz

# ── Logging setup ──────────────────────────────
# This prints everything happening in real time
# so you can see exactly what the bot is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

# ── Strategy Configuration ─────────────────────
# THIS IS WHERE YOU CONTROL EVERYTHING
# Change these numbers to adjust the strategy
CONFIG = {
    "symbol":           "MESM6",    # MES June contract
    "exchange":         "CME",
    "timezone":         "US/Eastern",

    # ORB Time Window
    "orb_start":        time(8, 0),   # 8:00 AM EST
    "orb_end":          time(8, 15),  # 8:15 AM EST — 15 min ORB

    # Trading Window
    "trade_start":      time(8, 15),  # Start trading after ORB forms
    "trade_end":        time(11, 0),  # Stop trading at 11 AM

    # Risk Management
    "contracts":        2,            # 2 contracts
    "stop_ticks":       60,           # 15 points = 60 ticks (15 x 4 ticks per point)
    "target_ticks":     92,           # 23 points = 92 ticks (20 x 4 ticks per point)
    "max_daily_loss":   350,          # Stop trading if down $350

    # Breakout confirmation
    "breakout_buffer":  1.25,         # Price must close 1 tick ABOVE/BELOW ORB
}
# ─────────────────────────────────────────────
# PART 2 — ORB RANGE BUILDER
# Watches price between 8:00-8:15 AM and
# records the high and low of that window
# ─────────────────────────────────────────────

class ORBRange:
    """
    Builds the Opening Range between 8:00-8:15 AM.
    Tracks the highest high and lowest low during that window.
    Once 8:15 hits — the range is LOCKED. No more updates.
    """

    def __init__(self):
        self.high        = None    # Highest price seen during ORB window
        self.low         = None    # Lowest price seen during ORB window
        self.locked      = False   # True after 8:15 AM — range is set
        self.breakout    = None    # "LONG" or "SHORT" once breakout confirmed
        self.trade_taken = False   # Only take ONE trade per day

    def update(self, price: float, current_time: time):
        """
        Called on every price tick between 8:00-8:15 AM.
        Updates high and low of the range.
        """
        tz      = pytz.timezone(CONFIG["timezone"])
        orb_start = CONFIG["orb_start"]
        orb_end   = CONFIG["orb_end"]

        # Only update during the ORB window
        if orb_start <= current_time < orb_end:
            if self.locked:
                return  # Already locked — ignore

            # Track highest high
            if self.high is None or price > self.high:
                self.high = price
                log.info(f"ORB High updated: {self.high}")

            # Track lowest low
            if self.low is None or price < self.low:
                self.low = price
                log.info(f"ORB Low updated: {self.low}")

        # Lock the range at 8:15 AM
        elif current_time >= orb_end and not self.locked:
            self.locked = True
            log.info(f"✅ ORB LOCKED — High: {self.high} | Low: {self.low} | Range: {round(self.high - self.low, 2)} points")

    def check_breakout(self, price: float) -> str | None:
        """
        After 8:15 AM — checks if price has broken
        above the ORB high (LONG) or below the ORB low (SHORT).
        Returns 'LONG', 'SHORT', or None.
        """
        if not self.locked:
            return None   # Range not set yet

        if self.trade_taken:
            return None   # Already traded today

        buffer = CONFIG["breakout_buffer"]

        # Price closed ABOVE ORB high — breakout long
        if price >= self.high + buffer:
            log.info(f"🟢 LONG BREAKOUT CONFIRMED at {price} | ORB High was {self.high}")
            return "LONG"

        # Price closed BELOW ORB low — breakout short
        elif price <= self.low - buffer:
            log.info(f"🔴 SHORT BREAKOUT CONFIRMED at {price} | ORB Low was {self.low}")
            return "SHORT"

        return None   # No breakout yet

    def range_size(self) -> float | None:
        """Returns the size of the ORB range in points."""
        if self.high and self.low:
            return round(self.high - self.low, 2)
        return None

    def is_ready(self) -> bool:
        """Returns True if range is locked and valid."""
        return self.locked and self.high is not None and self.low is not None
    # ─────────────────────────────────────────────
# PART 3 — RISK MANAGER
# Tracks your daily P&L and protects your
# Lucid account automatically
# ─────────────────────────────────────────────

class RiskManager:
    """
    Tracks daily P&L in real time.
    Automatically shuts the bot down if:
    - Daily loss limit is hit
    - Outside of trading hours
    - Trade already taken today
    """

    def __init__(self):
        self.daily_pnl      = 0.0    # Running P&L for today
        self.trades_today   = 0      # Number of trades taken today
        self.is_active      = True   # False = bot is shut down for the day
        self.shutdown_reason = None  # Why the bot stopped

    def can_trade(self, current_time: time) -> bool:
        """
        Returns True only if ALL conditions are met:
        - Bot is still active
        - Within trading hours
        - Under daily loss limit
        - Haven't exceeded trade limit
        """
        # Bot already shut down
        if not self.is_active:
            log.warning(f"🚫 Bot inactive: {self.shutdown_reason}")
            return False

        # Outside trading hours
        trade_start = CONFIG["trade_start"]
        trade_end   = CONFIG["trade_end"]

        if not (trade_start <= current_time <= trade_end):
            log.info(f"⏰ Outside trading hours ({trade_start} - {trade_end})")
            return False

        # Daily loss limit hit
        if self.daily_pnl <= -CONFIG["max_daily_loss"]:
            self.shutdown("Daily loss limit hit")
            return False

        return True

    def record_trade(self, pnl: float, direction: str):
        """
        Called after every trade closes.
        Updates daily P&L and logs the result.
        """
        self.daily_pnl    += pnl
        self.trades_today += 1

        result = "WIN 🟢" if pnl > 0 else "LOSS 🔴"

        log.info(f"─── TRADE CLOSED ───────────────────────")
        log.info(f"Direction  : {direction}")
        log.info(f"Trade P&L  : ${pnl:.2f}")
        log.info(f"Daily P&L  : ${self.daily_pnl:.2f}")
        log.info(f"Result     : {result}")
        log.info(f"────────────────────────────────────────")

        # Check if we should shut down after this trade
        if self.daily_pnl <= -CONFIG["max_daily_loss"]:
            self.shutdown("Daily loss limit reached after trade")

    def shutdown(self, reason: str):
        """Shuts the bot down for the rest of the day."""
        self.is_active       = False
        self.shutdown_reason = reason
        log.warning(f"🛑 BOT SHUTDOWN — Reason: {reason}")
        log.warning(f"🛑 Final Daily P&L: ${self.daily_pnl:.2f}")
        log.warning(f"🛑 Trades Today: {self.trades_today}")

    def daily_summary(self):
        """Prints end of day summary."""
        log.info(f"════════════════════════════════════════")
        log.info(f"📊 END OF DAY SUMMARY")
        log.info(f"Total Trades  : {self.trades_today}")
        log.info(f"Daily P&L     : ${self.daily_pnl:.2f}")
        log.info(f"Status        : {'✅ Active' if self.is_active else '🛑 Shutdown'}")
        if self.shutdown_reason:
            log.info(f"Shutdown Reason: {self.shutdown_reason}")
        log.info(f"════════════════════════════════════════")
        # ─────────────────────────────────────────────
# PART 4 — ORDER EXECUTOR
# Connects to Rithmic and fires real orders
# Handles entry, stop loss, and take profit
# ─────────────────────────────────────────────

class OrderExecutor:
    """
    Handles all order execution through Rithmic.
    Places entry, stop loss, and take profit
    as a bracket order — all at once.
    """

    def __init__(self, rithmic_client):
        self.client          = rithmic_client
        self.active_order_id = None    # Current open order ID
        self.position        = None    # "LONG", "SHORT", or None
        self.entry_price     = None    # Price we entered at
        self.stop_price      = None    # Stop loss price
        self.target_price    = None    # Take profit price

    def calculate_levels(self, direction: str, entry_price: float) -> tuple:
        """
        Calculates stop loss and take profit prices
        based on direction and tick settings in CONFIG.
        MES tick = 1.25 points
        """
        tick_size    = 1.25
        stop_ticks   = CONFIG["stop_ticks"]
        target_ticks = CONFIG["target_ticks"]

        stop_points   = stop_ticks   * tick_size   # 10 ticks = 2.5 points
        target_points = target_ticks * tick_size   # 20 ticks = 5.0 points

        if direction == "LONG":
            stop   = round(entry_price - stop_points,   2)
            target = round(entry_price + target_points, 2)
        else:  # SHORT
            stop   = round(entry_price + stop_points,   2)
            target = round(entry_price - target_points, 2)

        log.info(f"📐 Levels calculated:")
        log.info(f"   Direction : {direction}")
        log.info(f"   Entry     : {entry_price}")
        log.info(f"   Stop      : {stop}  ({stop_ticks} ticks)")
        log.info(f"   Target    : {target} ({target_ticks} ticks)")

        return stop, target

    async def execute_entry(self, direction: str, current_price: float):
        """
        Fires a bracket order:
        - Market order to enter
        - Stop loss placed immediately
        - Take profit placed immediately
        All three go in together. No manual steps.
        """
        if self.position:
            log.warning("⚠️ Already in a position — skipping entry")
            return

        contracts = CONFIG["contracts"]
        stop, target = self.calculate_levels(direction, current_price)

        log.info(f"🚀 FIRING {direction} ORDER")
        log.info(f"   Contracts : {contracts}")
        log.info(f"   Price     : {current_price}")

        try:
            # ── Entry order ──────────────────────────
            order = await self.client.submit_order(
                symbol      = CONFIG["symbol"],
                exchange    = CONFIG["exchange"],
                quantity    = contracts,
                order_type  = "MARKET",
                side        = "BUY" if direction == "LONG" else "SELL",
            )

            self.active_order_id = order.order_id
            self.position        = direction
            self.entry_price     = current_price
            self.stop_price      = stop
            self.target_price    = target

            # ── Stop loss order ───────────────────────
            await self.client.submit_order(
                symbol      = CONFIG["symbol"],
                exchange    = CONFIG["exchange"],
                quantity    = contracts,
                order_type  = "STOP",
                side        = "SELL" if direction == "LONG" else "BUY",
                price       = stop,
            )

            # ── Take profit order ─────────────────────
            await self.client.submit_order(
                symbol      = CONFIG["symbol"],
                exchange    = CONFIG["exchange"],
                quantity    = contracts,
                order_type  = "LIMIT",
                side        = "SELL" if direction == "LONG" else "BUY",
                price       = target,
            )

            log.info(f"✅ BRACKET ORDER PLACED SUCCESSFULLY")
            log.info(f"   Stop Loss  : {stop}")
            log.info(f"   Take Profit: {target}")

        except Exception as e:
            log.error(f"❌ ORDER FAILED: {e}")
            self.position = None   # Reset if order failed

    async def close_position(self, reason: str):
        """
        Manually closes the open position.
        Used for end of day flat or emergency exit.
        """
        if not self.position:
            log.info("No open position to close.")
            return

        contracts = CONFIG["contracts"]
        side      = "SELL" if self.position == "LONG" else "BUY"

        log.info(f"🔒 CLOSING POSITION — Reason: {reason}")

        try:
            await self.client.submit_order(
                symbol     = CONFIG["symbol"],
                exchange   = CONFIG["exchange"],
                quantity   = contracts,
                order_type = "MARKET",
                side       = side,
            )

            log.info(f"✅ Position closed successfully")
            self.position    = None
            self.entry_price = None

        except Exception as e:
            log.error(f"❌ CLOSE FAILED: {e}")

    def calculate_pnl(self, exit_price: float) -> float:
        """
        Calculates P&L when position closes.
        MES point value = $5.00
        """
        if not self.entry_price or not self.position:
            return 0.0

        point_value = 5.00
        contracts   = CONFIG["contracts"]

        if self.position == "LONG":
            pnl = (exit_price - self.entry_price) * point_value * contracts
        else:
            pnl = (self.entry_price - exit_price) * point_value * contracts

        return round(pnl, 2)
    # ─────────────────────────────────────────────
# PART 5 — MAIN ENGINE
# Ties everything together and runs the strategy
# Connects to Rithmic and processes every tick
# ─────────────────────────────────────────────

class ORBStrategy:
    """
    The brain of the operation.
    Connects all four parts together:
    - ORBRange    — builds and locks the range
    - RiskManager — protects the account
    - OrderExecutor — fires and manages orders
    Processes every price tick in real time.
    """

    def __init__(self):
        self.orb      = ORBRange()
        self.risk     = RiskManager()
        self.executor = None          # Set after Rithmic connects
        self.tz       = pytz.timezone(CONFIG["timezone"])

    def get_eastern_time(self) -> time:
        """Returns current time in Eastern timezone."""
        now = datetime.now(self.tz)
        return now.time()

    async def on_price_tick(self, price: float):
        """
        Called on EVERY price tick from Rithmic.
        This is the heartbeat of the strategy.
        Order of operations every tick:
        1. Get current time
        2. Update ORB range if within window
        3. Check if we can trade
        4. Check for breakout
        5. Fire order if breakout confirmed
        """
        current_time = self.get_eastern_time()

        # ── Step 1: Update ORB range ───────────────
        self.orb.update(price, current_time)

        # ── Step 2: Check if trading is allowed ────
        if not self.risk.can_trade(current_time):
            return

        # ── Step 3: Skip if ORB not ready yet ──────
        if not self.orb.is_ready():
            return

        # ── Step 4: Skip if already in a trade ─────
        if self.executor and self.executor.position:
            await self.check_exit(price, current_time)
            return

        # ── Step 5: Check for breakout ──────────────
        if not self.orb.trade_taken:
            breakout = self.orb.check_breakout(price)

            if breakout:
                self.orb.trade_taken = True
                await self.executor.execute_entry(breakout, price)

    async def check_exit(self, price: float, current_time: time):
        """
        Checks if we need to force close the position.
        Only triggers at 11:00 AM — end of trading window.
        Stop loss and take profit handle everything else.
        """
        trade_end = CONFIG["trade_end"]

        # Force flat at end of trading window
        if current_time >= trade_end:
            if self.executor.position:
                pnl = self.executor.calculate_pnl(price)
                self.risk.record_trade(pnl, self.executor.position)
                await self.executor.close_position("End of trading window — 11 AM flat")
                self.risk.daily_summary()

    async def run(self):
        """
        Main entry point.
        Connects to Rithmic and starts listening
        to price ticks for the strategy.
        """
        log.info("════════════════════════════════════════")
        log.info("🚀 Yeshua's 8AM ORB STRATEGY STARTING")
        log.info(f"   Symbol     : {CONFIG['symbol']}")
        log.info(f"   ORB Window : {CONFIG['orb_start']} - {CONFIG['orb_end']}")
        log.info(f"   Trade Hours: {CONFIG['trade_start']} - {CONFIG['trade_end']}")
        log.info(f"   Stop       : {CONFIG['stop_ticks']} ticks")
        log.info(f"   Target     : {CONFIG['target_ticks']} ticks")
        log.info(f"   Max Loss   : ${CONFIG['max_daily_loss']}")
        log.info("════════════════════════════════════════")

        try:
            from async_rithmic import RithmicClient

            # ── Connect to Rithmic ─────────────────
            # Replace these with your actual
            # Lucid Trading / Rithmic credentials
            client = RithmicClient(
    user        = "LT-O53J7UN5",
    password    = "4IY3yYLiy99l",
    system_name = "Lucid Trading",
    app_name    = "YeshuaORBStrategy",
    app_version = "1.0",
    url         = "wss://rituz00100.rithmic.com:443",
)

            await client.connect()
            log.info("✅ Connected to Rithmic successfully")

            # ── Set up executor ────────────────────
            self.executor = OrderExecutor(client)

            # ── Subscribe to price feed ────────────
            async def price_callback(tick_data):
                price = tick_data.get("last_price")
                if price:
                    await self.on_price_tick(float(price))

            await client.subscribe_to_market_data(
                symbol   = CONFIG["symbol"],
                exchange = CONFIG["exchange"],
                callback = price_callback,
            )

            log.info(f"📡 Subscribed to {CONFIG['symbol']} price feed")
            log.info("⏳ Waiting for 8:00 AM ORB window...")

            # ── Keep running until end of day ──────
            while self.risk.is_active:
                await asyncio.sleep(1)

                # Check for end of day at 11 AM
                current_time = self.get_eastern_time()
                if current_time >= CONFIG["trade_end"]:
                    if not self.executor.position:
                        log.info("📊 Trading window closed.")
                        self.risk.daily_summary()
                        break

            await client.disconnect()
            log.info("🔌 Disconnected from Rithmic")

        except Exception as e:
            log.error(f"❌ STRATEGY ERROR: {e}")
            raise
        # ─────────────────────────────────────────────
# RUN THE STRATEGY
# This is what actually starts everything
# Type: python3 orb_strategy.py in terminal
# ─────────────────────────────────────────────

if __name__ == "__main__":
    strategy = ORBStrategy()
    asyncio.run(strategy.run())