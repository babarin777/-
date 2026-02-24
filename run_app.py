import subprocess
import sys
import os
import time
import socket
import importlib.util

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_package(package_name):
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def run():
    print("="*50)
    print("   Excel 解析アプリ 診断・起動ツール")
    print("="*50)

    print(f"[情報] Python 実行パス: {sys.executable}")
    print(f"[情報] Python バージョン: {sys.version}")
    print(f"[情報] 実行ディレクトリ: {os.getcwd()}")

    # Required packages
    packages = ["streamlit", "pandas", "plotly", "openai", "openpyxl", "pyarrow"]
    missing_packages = []

    print("\n[1] 依存ライブラリの確認中...")
    for pkg in packages:
        if check_package(pkg):
            print(f"  ✅ {pkg.ljust(12)}: インストール済み")
        else:
            print(f"  ❌ {pkg.ljust(12)}: 未インストール")
            missing_packages.append(pkg)

    if missing_packages:
        print(f"\n[アクション] {len(missing_packages)} 個のライブラリが不足しています。インストールを開始します...")
        try:
            # Try to upgrade pip first
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("  ✅ ライブラリのインストールが完了しました。")
        except Exception as e:
            print(f"  ❌ インストール中にエラーが発生しました: {e}")
            print("  [ヒント] 管理者権限で実行するか、'pip install -r requirements.txt' を手動で試してください。")
            input("\nエンターキーを押して終了...")
            return

    print("\n[2] 起動準備...")
    # Port check
    port = 8501
    if is_port_in_use(port):
        print(f"  ⚠️  ポート {port} は既に使用されています。Streamlit は自動的に別のポートを使用します。")
    else:
        print(f"  ✅ ポート {port} は使用可能です。")

    # Final check for app file
    if not os.path.exists("excel_analyzer_app.py"):
        print("  ❌ エラー: 'excel_analyzer_app.py' が見つかりません。")
        input("\nエンターキーを押して終了...")
        return

    print("\n[3] Streamlit アプリケーションを起動します...")
    print("    (ブラウザが自動的に開かない場合は、コンソールに表示される URL をクリックしてください)\n")

    # Use 'python -m streamlit' as it's the most reliable way
    cmd = [sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py"]

    try:
        env = os.environ.copy()
        # Add current directory to PYTHONPATH to ensure local imports work if any
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

        # In some environments, Streamlit needs specific flags
        # env["STREAMLIT_SERVER_PORT"] = "8501"

        process = subprocess.Popen(cmd, env=env)

        # Monitor the process for the first 5 seconds
        for i in range(5):
            time.sleep(1)
            if process.poll() is not None:
                print(f"\n❌ エラー: アプリが予期せず終了しました (コード: {process.returncode})")
                print("  [ヒント] 上記の Streamlit ログを確認してください。")
                input("\nエンターキーを押して終了...")
                return

        print("\n✅ 起動に成功したようです。アプリを終了するにはこのウィンドウを閉じるか、Ctrl+C を押してください。")
        process.wait()

    except KeyboardInterrupt:
        print("\n[情報] ユーザーによって中断されました。")
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        input("\nエンターキーを押して終了...")

if __name__ == "__main__":
    run()
