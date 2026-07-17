#!/usr/bin/env python3
"""Super simple initialize test."""
import MetaTrader5 as mt5

print("Testing simple mt5.initialize()...")
result = mt5.initialize()
print(f"initialize() result: {result}")
if result:
    print("SUCCESS!")
    account_info = mt5.account_info()
    if account_info:
        print(f"Logged in to account: {account_info.login}")
    else:
        print("No account info (maybe not logged in)")
    mt5.shutdown()
else:
    last_err = mt5.last_error()
    print(f"FAILED! Error: {last_err}")
