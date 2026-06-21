# -*- coding: utf-8 -*-
import subprocess
import time
import sys
import os

def main():
    print("[*] Starting TaskPilot AI Full Agent System...")
    
    # 1. Start FastAPI Backend
    print("[1/3] Starting backend API (main.py)...")
    api_process = subprocess.Popen([sys.executable, "main.py"])
    time.sleep(3) # Wait for backend to be ready
    
    # 2. Start Streamlit Dashboard
    print("[2/3] Starting Streamlit dashboard (app.py)...")
    dashboard_process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py"])
    time.sleep(2)
    
    # 3. Start Autonomous Agent Worker
    print("[3/3] Starting Autonomous Agent Worker (autonomous_agent.py)...")
    agent_process = subprocess.Popen([sys.executable, "autonomous_agent.py"])
    
    try:
        print("\n[OK] All systems running!")
        print("     Dashboard: http://localhost:8501")
        print("     API:       http://localhost:8000")
        print("     Press Ctrl+C to shut down.\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down systems...")
        agent_process.terminate()
        dashboard_process.terminate()
        api_process.terminate()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
