#!/usr/bin/env python3
"""Comprehensive MT5 diagnostic script."""
import sys
import os
import subprocess

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("MT5 CONNECTION DIAGNOSTIC TOOL")
print("=" * 80)
print()

# 1. Check Python version
print("1. Checking Python version...")
print(f"   Python version: {sys.version}")

# 2. Check if MetaTrader5 package is installed
print("\n2. Checking MetaTrader5 package...")
try:
    import MetaTrader5 as mt5
    print(f"   ✓ MetaTrader5 package installed: {mt5.__version__}")
    print(f"   MT5 available: True")
except ImportError as e:
    print(f"   ✗ MetaTrader5 package NOT installed: {str(e)}")
    print("\n   To install: pip install MetaTrader5==5.0.45")
    sys.exit(1)

# 3. Check OS
print("\n3. Checking operating system...")
print(f"   OS: {os.name}")
if os.name != "nt":
    print("   ✗ WARNING: MetaTrader5 Python package only supports Windows!")

# 4. Check if MT5 terminal process is running
print("\n4. Checking if MT5 terminal is running...")
try:
    import psutil
    terminal_found = False
    terminal_pids = []
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            name = proc.info["name"].lower()
            if name in ["terminal.exe", "terminal64.exe"]:
                terminal_found = True
                terminal_pids.append(proc.info["pid"])
                print(f"   ✓ Found terminal process: {proc.info['name']} (PID: {proc.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not terminal_found:
        print("   ✗ MT5 terminal NOT running!")
        print("\n   >> ACTION NEEDED: Open MetaTrader 5 terminal and log in!")
except ImportError:
    print("   ⚠ psutil not available - can't check running processes")

# 5. Check .env file and MT5 config
print("\n5. Checking configuration...")
from app.core.config.settings import settings
print(f"   MT5_LOGIN: {settings.MT5_LOGIN if settings.MT5_LOGIN else 'NOT SET'}")
print(f"   MT5_PASSWORD: {('*' * 10) if settings.MT5_PASSWORD else 'NOT SET'}")
print(f"   MT5_SERVER: {settings.MT5_SERVER if settings.MT5_SERVER else 'NOT SET'}")
print(f"   MT5_PATH (from .env): {settings.MT5_PATH if settings.MT5_PATH else 'NOT SET'}")

# 6. Check auto-detected paths
print("\n6. Checking auto-detected MT5 installation paths...")
from app.infrastructure.mt5.connector import (
    find_mt5_installation_paths,
    validate_mt5_path,
    auto_detect_mt5_path
)
candidate_paths = find_mt5_installation_paths()
valid_paths = []
for path in candidate_paths:
    valid = validate_mt5_path(path)
    if valid:
        print(f"   ✓ Valid path found: {valid}")
        valid_paths.append(valid)
if not valid_paths:
    print("   ⚠ No auto-detected valid paths found")

auto_path = auto_detect_mt5_path()
print(f"   Auto-detected path: {auto_path if auto_path else 'None'}")

# 7. Check path from .env
print("\n7. Checking configured MT5_PATH...")
if settings.MT5_PATH:
    env_path_valid = validate_mt5_path(settings.MT5_PATH)
    if env_path_valid:
        print(f"   ✓ Configured path is valid: {env_path_valid}")
    else:
        print(f"   ✗ Configured path is invalid: {settings.MT5_PATH}")
        print("   Checking for terminal64.exe/terminal.exe...")
        if os.path.isdir(settings.MT5_PATH):
            files = os.listdir(settings.MT5_PATH)
            print(f"   Files in directory: {', '.join(files[:20])}")

# 8. Try simplified connection (just initialize without credentials first)
print("\n8. Testing simplified connection (just initialize)...")
if os.name == "nt":
    init_result = False
    try:
        # Try initializing without any parameters first
        print("   Trying mt5.initialize() (no params)...")
        init_result = mt5.initialize()
        print(f"   Result: {init_result}")
        if init_result:
            print("   ✓ SUCCESS: initialize() worked!")
            # Check if logged in
            account_info = mt5.account_info()
            if account_info:
                print(f"   ✓ Already logged in to account: {account_info.login} on {account_info.server}")
            else:
                print("   ℹ Not logged in yet - need to call mt5.login()")
            mt5.shutdown()
        else:
            last_err = mt5.last_error()
            print(f"   ✗ initialize() failed: error code {last_err[0]} - {last_err[1]}")

            # Try with auto-detected path
            if auto_path:
                print(f"\n   Trying mt5.initialize(path='{auto_path}')...")
                init_result = mt5.initialize(path=auto_path)
                if init_result:
                    print(f"   ✓ SUCCESS with path: {auto_path}")
                    account_info = mt5.account_info()
                    if account_info:
                        print(f"   ✓ Logged in to account: {account_info.login} on {account_info.server}")
                    mt5.shutdown()
                else:
                    last_err = mt5.last_error()
                    print(f"   ✗ Still failed with path: {last_err}")
    except Exception as e:
        print(f"   ✗ Exception during initialize: {str(e)}")
        import traceback
        print(f"   Stack trace: {traceback.format_exc()}")


print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)
print("\nKey checks:")
if terminal_found:
    print("✓ MT5 terminal is running")
else:
    print("✗ MT5 terminal is NOT running (CRITICAL)")

print("\nPlease follow these steps:")
print("1. Open MetaTrader 5 terminal")
print("2. Log in to your account")
print("3. Make sure terminal stays open")
print("4. Then run the test again!")

