import os
import subprocess
import sys
import webbrowser
import time
import socket

def check_dependencies():
    """必要なライブラリがインストールされているか確認する"""
    required = ["streamlit", "pandas", "openpyxl", "plotly", "openai"]
    missing = []
    for lib in required:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)

    if missing:
        print(f"エラー: 以下のライブラリが見つかりません: {', '.join(missing)}")
        print("以下のコマンドを実行してインストールしてください:")
        print(f"{sys.executable} -m pip install {' '.join(missing)}")
        return False
    return True

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def main():
    print("--- Excelデータ解析アプリ 起動ツール ---")

    # スクリプトの場所をカレントディレクトリに設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        os.chdir(script_dir)
    except Exception as e:
        print(f"警告: 作業ディレクトリの変更に失敗しました: {e}")

    # 診断情報の表示
    print(f"Pythonパス: {sys.executable}")
    print(f"実行ディレクトリ: {os.getcwd()}")

    if os.getcwd().lower().endswith("system32"):
        print("\n[!] 警告: システムディレクトリ(system32)で実行されています。")
        print("アプリのファイルがあるフォルダに移動(cd)してから実行することをお勧めします。")

    if not check_dependencies():
        input("\n[Enter] キーを押して終了します...")
        sys.exit(1)

    port = 8501
    if is_port_in_use(port):
        print(f"警告: ポート {port} は既に使用されています。別のポートで起動を試みます...")
        # Streamlitは自動的に次のポートを探しますが、明示的に警告します。

    print("アプリケーションを起動しています...")

    # ログファイルの設定
    log_file = "startup_debug.log"

    # Streamlitを起動
    cmd = [sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py", "--server.port", str(port)]

    try:
        f = None
        try:
            f = open(log_file, "w", encoding="utf-8")
            process = subprocess.Popen(cmd, stdout=f, stderr=f)
        except PermissionError:
            print(f"\n警告: '{log_file}' への書き込み権限がありません。ログ出力をスキップします。")
            process = subprocess.Popen(cmd)

        # サーバーの起動待ち
        print("サーバーの起動を待機中 (約10秒)...")
        for i in range(10):
            time.sleep(1)
            print(f"{10-i}...", end=" ", flush=True)
        print("\n")

        url = f"http://localhost:{port}"
        print(f"ブラウザで {url} を開きます。")
        webbrowser.open(url)

        print("\n--- 起動チェック ---")
        if process.poll() is not None:
            print("エラー: アプリが予期せず終了しました。")
            print(f"詳細なエラー内容は '{log_file}' を確認してください。")
        else:
            print("アプリケーションがバックグラウンドで動作しています。")
            print("アクセスできない場合は、ブラウザで以下のURLを試してください:")
            print(f"  1. http://localhost:{port}")
            print(f"  2. http://127.0.0.1:{port}")
            print(f"\nログファイル '{log_file}' が作成されました。問題がある場合はこの内容を確認してください。")

        print("\n[Ctrl+C] を押すとアプリを終了します。")
        process.wait()

    except KeyboardInterrupt:
        print("\nアプリケーションを終了します。")
        process.terminate()
    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")
        input("\n[Enter] キーを押して終了します...")
    finally:
        if f:
            f.close()

if __name__ == "__main__":
    main()
