import subprocess
import sys
import os
import time
import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def run():
    print("="*50)
    print("Excel 解析アプリ 起動スクリプト")
    print("="*50)

    # Check Python version
    print(f"Python バージョン: {sys.version}")

    # Check dependencies
    print("\n依存ライブラリのチェック中...")
    try:
        import streamlit
        import pandas
        import plotly
        import openai
        import openpyxl
        print("✅ すべての必須ライブラリがインストールされています。")
    except ImportError as e:
        print(f"❌ ライブラリが不足しています: {e}")
        print("インストールを開始します...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ インストールが完了しました。")
        except Exception as e:
            print(f"❌ インストールの実行中にエラーが発生しました: {e}")
            print("手動で 'pip install -r requirements.txt' を実行してください。")
            input("\nエンターキーを押して終了...")
            return

    # Check port 8501
    port = 8501
    if is_port_in_use(port):
        print(f"\n⚠️ 警告: ポート {port} は既に使用されています。")
        print("別のポートで起動を試みます、または既存のプロセスを終了してください。")

    # Run streamlit
    print("\nStreamlit を起動しています...")
    # Use 'python -m streamlit' by default for better compatibility
    cmd = [sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py"]

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

        # Start the process
        process = subprocess.Popen(cmd, env=env)

        # Wait a bit to see if it crashes immediately
        time.sleep(3)
        if process.poll() is not None:
            # It exited
            print(f"\n❌ Streamlit が起動直後に終了しました (終了コード: {process.returncode})")
            print("依存ライブラリが正しくインストールされているか、ポート 8501 が空いているか確認してください。")
            input("\nエンターキーを押して終了...")
        else:
            # Still running, wait for it
            process.wait()

    except KeyboardInterrupt:
        print("\nアプリを終了しました。")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Streamlit が異常終了しました (終了コード: {e.returncode})")
        print("エラー内容を確認してください。")
        input("\nエンターキーを押して終了...")
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        input("\nエンターキーを押して終了...")

if __name__ == "__main__":
    run()
