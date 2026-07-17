#!/usr/bin/env python3
"""Ultimate MT5 connection test."""
import MetaTrader5 as mt5
import time

print("=== ULTIMATE MT5 CONNECTION TEST ===\n")

# Step 1: Clean up any existing connection
print("1. Cleaning up any existing connection...")
try:
    mt5.shutdown()
    time.sleep(1)
    print("   ✓ Shutdown complete\n")
except Exception as e:
    print(f"   ℹ Shutdown failed (probably none active): {e}\n")

# Step 2: Try initialize with NO parameters at all
print("2. Trying mt5.initialize() (NO PARAMETERS)...")
init_result = mt5.initialize()
last_err = mt5.last_error()
print(f"   Result: {init_result}")
print(f"   Last error: {last_err}\n")

if init_result:
    print("🎉 INITIALIZE SUCCESS!\n")

    # Step 3: Check account info
    print("3. Checking account info...")
    account_info = mt5.account_info()
    if account_info:
        print("   ✓ Account info found!")
        print(f"   Login: {account_info.login}")
        print(f"   Name: {account_info.name}")
        print(f"   Server: {account_info.server}")
        print(f"   Balance: {account_info.balance} {account_info.currency}")
        print(f"   Equity: {account_info.equity} {account_info.currency}")
    else:
        print("   ⚠ No account info (terminal not logged in?)")
        last_err = mt5.last_error()
        print(f"   Last error: {last_err}")

    # Step 4: Check terminal info
    print("\n4. Checking terminal info...")
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print("   ✓ Terminal info found!")
        print(f"   Connected: {terminal_info.connected}")
        print(f"   Trade allowed: {terminal_info.trade_allowed}")
    else:
        print("   ⚠ No terminal info")

    # Clean up
    mt5.shutdown()
else:
    print("❌ INITIALIZE FAILED!")
    print("\nPossible reasons:")
    print("- Terminal not running")
    print("- Terminal not logged in")
    print("- IPC connections disabled in terminal settings")
