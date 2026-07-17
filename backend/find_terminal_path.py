#!/usr/bin/env python3
"""Find full path of running terminal64.exe or terminal.exe."""
import psutil
import os

print("Finding running terminal process...")
terminal_dir = None
for proc in psutil.process_iter(["name", "pid", "exe"]):
    try:
        name = proc.info["name"].lower()
        if name in ["terminal.exe", "terminal64.exe"]:
            print(f"Found process: {proc.info['name']}")
            print(f"PID: {proc.info['pid']}")
            print(f"EXE path: {proc.info['exe']}")
            if proc.info["exe"]:
                terminal_dir = os.path.dirname(proc.info["exe"])
                print(f"Terminal directory: {terminal_dir}")
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue

if terminal_dir:
    print("\nNow trying mt5.initialize with this directory...")
    import MetaTrader5 as mt5
    result = mt5.initialize(path=terminal_dir)
    print(f"initialize() with path result: {result}")
    if result:
        print("SUCCESS!")
        account_info = mt5.account_info()
        if account_info:
            print(f"Logged in to account: {account_info.login}")
            print(f"Server: {account_info.server}")
        else:
            print("No account info - not logged in to terminal")
        mt5.shutdown()
    else:
        last_err = mt5.last_error()
        print(f"FAILED! Error: {last_err}")
