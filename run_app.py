import os
import subprocess
import sys
import webbrowser
import time

def check_dependencies():
    """必要なライブラリがインストールされているか確認する"""
    try:
        import streamlit
        import pandas
        import openpyxl
        import plotly
        import openai
        return True
    except ImportError as e:
        print(f"エラー: 必要なライブラリが見つかりません: {e}")
        print("pip install -r requirements.txt を実行してインストールしてください。")
        return False

def main():
    print("--- Excelデータ解析アプリ 起動ツール ---")

    if not check_dependencies():
        sys.exit(1)

    print("アプリケーションを起動しています...")

    # Streamlitをバックグラウンドで起動
    # コマンド: streamlit run excel_analyzer_app.py
    cmd = [sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py"]

    try:
        # Streamlitサーバーを起動
        process = subprocess.Popen(cmd)

        # サーバーの起動待ち（少し時間がかかる場合がある）
        print("サーバーの起動を待機中...")
        time.sleep(5)

        url = "http://localhost:8501"
        print(f"\nブラウザで {url} を開きます。")
        webbrowser.open(url)

        print("\nアプリケーションが正常に起動しました。")
        print("ブラウザが自動的に開かない場合は、上記のURLに直接アクセスしてください。")
        print("\n[Ctrl+C] で終了します。")

        process.wait()
    except KeyboardInterrupt:
        print("\nアプリケーションを終了します。")
        process.terminate()
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
