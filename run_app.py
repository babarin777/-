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

    # スクリプトの場所を作業ディレクトリに設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir:
        try:
            os.chdir(script_dir)
        except Exception as e:
            print(f"警告: 作業ディレクトリの変更に失敗しました: {e}")

    # 診断情報の表示
    print(f"Pythonバージョン: {sys.version}")
    print(f"Pythonパス: {sys.executable}")
    print(f"実行ディレクトリ: {os.getcwd()}")

    # ファイルの存在確認
    app_file = "excel_analyzer_app.py"
    if not os.path.exists(app_file):
        print(f"エラー: {app_file} が見つかりません。")
        print(f"現在のディレクトリにあるファイル: {os.listdir('.')}")
        input("\n[Enter] キーを押して終了します...")
        sys.exit(1)

    if os.getcwd().lower().endswith("system32"):
        print("\n[!] 警告: システムディレクトリ(system32)で実行されています。")
        print("アプリのファイルがあるフォルダに移動(cd)してから実行することをお勧めします。")

    if not check_dependencies():
        input("\n[Enter] キーを押して終了します...")
        sys.exit(1)

    # 空いているポートを探す
    port = 8501
    while is_port_in_use(port):
        print(f"ポート {port} は既に使用されています。次のポートを試します...")
        port += 1

    print(f"使用ポート: {port}")
    print("アプリケーションを起動しています...")

    # ログファイルの設定
    log_file = "startup_debug.log"

    # Streamlitを起動
    # server.addressを 127.0.0.1 に固定して互換性を高める
    cmd = [sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py",
           "--server.port", str(port), "--server.address", "127.0.0.1"]

    try:
        f = None
        try:
            f = open(log_file, "w", encoding="utf-8")
            process = subprocess.Popen(cmd, stdout=f, stderr=f)
        except PermissionError:
            print(f"\n警告: '{log_file}' への書き込み権限がありません。ログ出力をターミナルに表示します。")
            process = subprocess.Popen(cmd)

        # サーバーの起動待ち
        print("サーバーの起動を待機中 (約10秒)...")
        for i in range(10):
            time.sleep(1)
            print(f"{10-i}...", end=" ", flush=True)
        print("\n")

        url = f"http://127.0.0.1:{port}"
        print(f"ブラウザで {url} を開きます...")
        # サーバーが立ち上がる前にブラウザが開いて「接続拒否」になるのを防ぐため、少し待つ
        time.sleep(2)
        webbrowser.open(url)

        print("\n--- 起動チェック ---")
        if process.poll() is not None:
            print("エラー: アプリが予期せず終了しました。")
            if f:
                print("--- エラーログの内容 ---")
                with open(log_file, "r", encoding="utf-8") as read_f:
                    print(read_f.read())
                print("------------------------")
            else:
                print("ログファイルを作成できなかったため、詳細は上記のエラーを確認してください。")
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
