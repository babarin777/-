import subprocess
import sys
import os
import time
import socket
import importlib.util
import webbrowser
import logging

# Setup logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("startup_debug.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_package(package_name):
    try:
        spec = importlib.util.find_spec(package_name)
        return spec is not None
    except Exception:
        return False

def run():
    logger.info("="*50)
    logger.info("   Excel 解析アプリ 診断・起動ツール (高度なデバッグモード)")
    logger.info("="*50)

    logger.info(f"Python 実行パス: {sys.executable}")
    logger.info(f"Python バージョン: {sys.version}")
    logger.info(f"実行ディレクトリ: {os.getcwd()}")

    # Check for required files
    files = ["excel_analyzer_app.py", "requirements.txt"]
    for f in files:
        if os.path.exists(f):
            logger.info(f"✅ ファイル確認: {f}")
        else:
            logger.error(f"❌ エラー: {f} が見つかりません。")
            input("\nエンターキーを押して終了...")
            return

    # Required packages
    packages = ["streamlit", "pandas", "plotly", "openai", "openpyxl", "pyarrow"]
    missing_packages = []

    logger.info("\n[1] 依存ライブラリの確認中...")

    # Check if pip is available
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("✅ pip: 利用可能")
    except Exception:
        logger.error("❌ エラー: 'pip' が見つかりません。")
        input("\nエンターキーを押して終了...")
        return

    for pkg in packages:
        if check_package(pkg):
            logger.info(f"  ✅ {pkg.ljust(12)}: インストール済み")
        else:
            logger.warning(f"  ⚠️  {pkg.ljust(12)}: 未インストール")
            missing_packages.append(pkg)

    if missing_packages:
        logger.info(f"\n[アクション] {len(missing_packages)} 個のライブラリが不足しています。インストールを開始します...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            logger.info("✅ ライブラリのインストールが完了しました。")
        except Exception as e:
            logger.error(f"❌ インストール中にエラーが発生しました: {e}")
            logger.info("[ヒント] 管理者権限で実行するか、インターネット接続を確認してください。")
            input("\nエンターキーを押して終了...")
            return

    logger.info("\n[2] 起動準備...")
    port = 8501
    while is_port_in_use(port):
        logger.info(f"  ℹ️  ポート {port} は使用中です。次のポートを確認します...")
        port += 1
    logger.info(f"✅ ポート {port} を使用して起動を試みます。")

    logger.info("\n[3] Streamlit アプリケーションを起動します...")

    # Command to run streamlit
    cmd = [sys.executable, "-m", "streamlit", "run", "excel_analyzer_app.py", "--server.port", str(port)]

    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")

        # Start the process and capture output to log file as well
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Open browser after a short delay
        url = f"http://localhost:{port}"
        logger.info(f"🌍 ブラウザで以下を開いてください: {url}")

        def open_browser():
            time.sleep(3)
            logger.info("🚀 ブラウザを自動的に開きます...")
            webbrowser.open(url)

        # We can't easily thread here without complex setup, so we just log and wait

        # Monitor output and print to console
        logger.info("--- アプリのログ出力を開始します ---")

        # Read output in a loop
        for line in iter(process.stdout.readline, ""):
            if line:
                # Log without the default logger formatting for cleaner app output
                sys.stdout.write(f"[App] {line}")
                sys.stdout.flush()
                # Also save to debug log
                with open("startup_debug.log", "a", encoding='utf-8') as f:
                    f.write(f"[App] {line}")

            if process.poll() is not None:
                break

        rc = process.poll()
        if rc != 0:
            logger.error(f"\n❌ エラー: アプリが異常終了しました (コード: {rc})")
            input("\nエンターキーを押して終了...")

    except KeyboardInterrupt:
        logger.info("\n[情報] ユーザーによって中断されました。")
    except Exception as e:
        logger.error(f"\n❌ 予期しないエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        input("\nエンターキーを押して終了...")

if __name__ == "__main__":
    run()
