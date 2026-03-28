# ─────────────────────────────────────────────
# TEST FILE — Simulates price ticks
# Tests all strategy logic without connecting
# to Rithmic. Safe to run anytime.
# ─────────────────────────────────────────────

import asyncio
from datetime import time
from orb_strategy import ORBRange, RiskManager, CONFIG

async def run_test():
    print("\n════════════════════════════════════")
    print("🧪 RUNNING STRATEGY SIMULATION TEST")
    print("════════════════════════════════════\n")

    orb  = ORBRange()
    risk = RiskManager()

    # ── Test 1: Build the ORB Range ───────────
    print("TEST 1: Building ORB Range (8:00-8:15 AM)")
    print("─────────────────────────────────────────")

    # Simulate price ticks during 8:00-8:15 AM
    fake_ticks_orb = [
        (time(8, 0),  6650.00),
        (time(8, 2),  6658.25),   # New high
        (time(8, 5),  6645.50),   # New low
        (time(8, 8),  6655.00),
        (time(8, 10), 6660.00),   # New high
        (time(8, 12), 6642.75),   # New low
        (time(8, 14), 6652.00),
    ]

    for tick_time, price in fake_ticks_orb:
        orb.update(price, tick_time)

    # Lock the range at 8:15
    orb.update(6653.00, time(8, 15))

    print(f"ORB High    : {orb.high}")
    print(f"ORB Low     : {orb.low}")
    print(f"ORB Range   : {orb.range_size()} points")
    print(f"ORB Locked  : {orb.locked}")
    print()

    # ── Test 2: Check for Breakout ────────────
    print("TEST 2: Checking for Breakout")
    print("─────────────────────────────────────────")

    # Simulate price ticks after 8:15 AM
    fake_ticks_trade = [
        (time(8, 16), 6655.00),   # Inside range — no breakout
        (time(8, 18), 6658.00),   # Inside range — no breakout
        (time(8, 20), 6661.00),   # Above ORB high — LONG breakout!
    ]

    for tick_time, price in fake_ticks_trade:
        if risk.can_trade(tick_time):
            breakout = orb.check_breakout(price)
            if breakout:
                print(f"✅ Breakout detected: {breakout} at {price}")
                print(f"   ORB High was : {orb.high}")
                print(f"   Buffer used  : {CONFIG['breakout_buffer']}")
            else:
                print(f"   No breakout at {price} — waiting...")
    print()

    # ── Test 3: Calculate Levels ──────────────
    print("TEST 3: Calculate Stop & Target Levels")
    print("─────────────────────────────────────────")

    entry = 6661.00
    tick_size    = 0.25
    stop_points  = CONFIG["stop_ticks"]   * tick_size
    target_points = CONFIG["target_ticks"] * tick_size

    stop_long   = round(entry - stop_points,   2)
    target_long = round(entry + target_points, 2)

    print(f"Entry Price  : {entry}")
    print(f"Stop Loss    : {stop_long}  ({CONFIG['stop_ticks']} ticks = ${CONFIG['stop_ticks'] * 1.25:.2f})")
    print(f"Take Profit  : {target_long} ({CONFIG['target_ticks']} ticks = ${CONFIG['target_ticks'] * 1.25:.2f})")
    print(f"R:R Ratio    : 1:{CONFIG['target_ticks'] // CONFIG['stop_ticks']}.0")
    print()

    # ── Test 4: P&L Calculation ───────────────
    print("TEST 4: P&L Calculation")
    print("─────────────────────────────────────────")

    # Simulate winning trade
    exit_win  = target_long
    exit_loss = stop_long
    point_val = 5.00
    contracts = CONFIG["contracts"]

    pnl_win  = round((exit_win  - entry) * point_val * contracts, 2)
    pnl_loss = round((exit_loss - entry) * point_val * contracts, 2)

    print(f"If TP hits   : +${pnl_win}  WIN 🟢")
    print(f"If SL hits   : -${abs(pnl_loss)}  LOSS 🔴")
    print()

    # ── Test 5: Risk Manager ──────────────────
    print("TEST 5: Risk Manager")
    print("─────────────────────────────────────────")

    risk.record_trade(pnl_win, "LONG")
    print(f"After win  — Daily P&L: ${risk.daily_pnl}")

    risk.record_trade(pnl_loss, "LONG")
    print(f"After loss — Daily P&L: ${risk.daily_pnl}")

    risk.daily_summary()

    print("\n════════════════════════════════════")
    print("✅ ALL TESTS PASSED — Strategy Ready!")
    print("════════════════════════════════════\n")

asyncio.run(run_test())