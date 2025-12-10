#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launcher for all services
Starts Web Server and API Proxy Server
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def main():
    script_dir = Path(__file__).parent
    
    print("=" * 70)
    print(" Netcafe Automation Config Tool - Launcher")
    print("=" * 70)
    print()
    
    # Start Web Server
    print("Starting Web Server (port 8000)...")
    web_process = subprocess.Popen(
        [sys.executable, str(script_dir / "web_server.py")],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
    )
    
    time.sleep(1)
    
    # Start API Proxy Server
    print("Starting API Proxy Server (port 8001)...")
    api_process = subprocess.Popen(
        [sys.executable, str(script_dir / "ha_proxy_server.py")],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
    )
    
    time.sleep(1)
    
    print()
    print("=" * 70)
    print(" All services started!")
    print("=" * 70)
    print()
    print("Web URL:   http://localhost:8000/netcafe_config_tool.html")
    print("Proxy API: http://localhost:8001")
    print()
    print("Opening browser...")
    print()
    print("=" * 70)
    print()
    print("Tips:")
    print("  - Keep this window and the other 2 windows open")
    print("  - Closing this window will stop all services")
    print("  - Close all windows when done")
    print()
    print("Press Ctrl+C to stop all services...")
    print()
    
    # 打开浏览器
    time.sleep(1)
    webbrowser.open('http://localhost:8000/netcafe_config_tool.html')
    
    try:
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if processes are still running
            if web_process.poll() is not None or api_process.poll() is not None:
                print("\nService stopped detected, shutting down...")
                break
    except KeyboardInterrupt:
        print("\n\nStopping all services...")
    
    # Stop all processes
    try:
        web_process.terminate()
        api_process.terminate()
        time.sleep(1)
        print("All services stopped")
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        input("\nPress Enter to exit...")
