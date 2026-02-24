import subprocess
import sys
import os

def run():
    print("Excel 解析アプリを起動しています...")
    try:
        # Check if streamlit is installed
        import streamlit
    except ImportError:
        print("必要なライブラリが見つかりません。インストールを開始します...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # Run streamlit
    try:
        subprocess.run(["streamlit", "run", "excel_analyzer_app.py"])
    except FileNotFoundError:
        # If streamlit command is not in PATH, try running as a module
        subprocess.run([sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py"])

if __name__ == "__main__":
    run()
