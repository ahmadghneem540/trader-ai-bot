#!/usr/bin/env python3
"""Simple MT5 connection verification test script."""
import sys
import os

# Add the current directory to Python path to import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.infrastructure.mt5 import get_mt5_connector


def test_mt5_connection():
    print("=" * 80)
    print("TRADERAI - MT5 CONNECTION TEST")
    print("=" * 80)
    print()

    # Step 1: Initialize connector
    print("1. Initializing MT5Connector...")
    try:
        connector = get_mt5_connector()
        print("   ✓ MT5Connector initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed to initialize MT5Connector: {str(e)}")
        return 1

    print()

    # Step 2: Try to connect
    print("2. Attempting to connect to MT5...")
    try:
        # Use connect method
        result = connector.connect()
        if result.get("success"):
            print("   ✓ Connected to MT5 successfully!")
        else:
            print(f"   ✗ Connection failed: {result.get('error')}")
            stage = result.get("stage")
            if stage:
                print(f"     Stage: {stage}")
            last_error = result.get("mt5_last_error")
            if last_error:
                print(f"     Last error code: {last_error[0]}")
                print(f"     Last error description: {last_error[1]}")
            suggested = result.get("suggested_solution")
            if suggested:
                print(f"     Suggested solution: {suggested}")
            return 1
    except Exception as e:
        print(f"   ✗ Connection attempt threw an exception: {str(e)}")
        import traceback
        print("     Exception trace:")
        print("     " + traceback.format_exc().replace("\n", "\n     "))
        return 1

    print()

    # Step 3: Check detailed status
    print("3. Checking detailed status...")
    try:
        status = connector.get_detailed_status()
        print(f"   Connected: {status.get('connected')}")
        print(f"   Terminal: {status.get('terminal')}")
        print(f"   Server: {status.get('server')}")
        print(f"   Checks:")
        checks = status.get("checks", {})
        for check_name, check_val in checks.items():
            status_str = "✓" if check_val else "✗"
            print(f"     {status_str} {check_name}")
        if not status.get("connected"):
            print(f"   Last error: {status.get('last_error')}")
            return 1
    except Exception as e:
        print(f"   ✗ Failed to get detailed status: {str(e)}")
        return 1

    print()

    # Step 4: Get account info
    print("4. Retrieving account information...")
    try:
        account_info = connector.get_account_info()
        if account_info:
            print(f"   ✓ Account info retrieved!")
            print(f"   Login: {account_info.get('login')}")
            print(f"   Name: {account_info.get('name')}")
            print(f"   Server: {account_info.get('server')}")
            print(f"   Balance: {account_info.get('balance')} {account_info.get('currency', '')}")
            print(f"   Equity: {account_info.get('equity')} {account_info.get('currency', '')}")
            print(f"   Leverage: 1:{account_info.get('leverage')}")
        else:
            print("   ✗ Could not retrieve account info")
            return 1
    except Exception as e:
        print(f"   ✗ Failed to get account info: {str(e)}")
        import traceback
        print("     Exception trace:")
        print("     " + traceback.format_exc().replace("\n", "\n     "))
        return 1

    print()

    # Step 5: Check XAUUSD symbol
    print("5. Checking XAUUSD symbol availability...")
    symbol_name = "XAUUSD"
    try:
        symbol_info = None
        # Try to get symbol info
        if hasattr(connector, "_ensure_symbol"):
            symbol_ok = connector._ensure_symbol(symbol_name)
            print(f"   Symbol selected: {symbol_ok}")

        # Let's directly use mt5 if available
        from app.infrastructure.mt5.connector import MT5_AVAILABLE, mt5
        if MT5_AVAILABLE:
            symbol_info = mt5.symbol_info(symbol_name)
        if symbol_info:
            print(f"   ✓ Symbol {symbol_name} found!")
            print(f"   Name: {symbol_info.name}")
            print(f"   Description: {symbol_info.description}")
            print(f"   Digits: {symbol_info.digits}")
            print(f"   Point: {symbol_info.point}")
        else:
            print(f"   ✗ Symbol {symbol_name} NOT found!")
            return 1
    except Exception as e:
        print(f"   ✗ Failed to check symbol: {str(e)}")
        import traceback
        print("     Exception trace:")
        print("     " + traceback.format_exc().replace("\n", "\n     "))
        return 1

    print()

    # Step 6: Get tick data
    print("6. Retrieving tick data...")
    try:
        tick = connector.get_tick(symbol_name)
        if tick:
            print("   ✓ Tick data retrieved!")
            print(f"   Time: {tick.get('time')}")
            print(f"   Bid: {tick.get('bid')}")
            print(f"   Ask: {tick.get('ask')}")
            print(f"   Last: {tick.get('last')}")
            print(f"   Volume: {tick.get('volume')}")
        else:
            print("   ✗ Could not retrieve tick data")
            return 1
    except Exception as e:
        print(f"   ✗ Failed to get tick data: {str(e)}")
        import traceback
        print("     Exception trace:")
        print("     " + traceback.format_exc().replace("\n", "\n     "))
        return 1

    print()
    print("=" * 80)
    print("ALL TESTS PASSED! ✨")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    exit_code = test_mt5_connection()
    print()
    print(f"Test finished with exit code: {exit_code}")
    sys.exit(exit_code)
