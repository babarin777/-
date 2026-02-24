import sys
import time
from playwright.sync_api import sync_playwright

def launch_chrome_and_google():
    """
    Playwrightを使用してChromeを自動的に起動し、Googleのホームページを表示します。
    """
    print("ブラウザを起動しています...")

    with sync_playwright() as p:
        # headless=False にすることで、ブラウザの画面が表示されます。
        # slow_mo を入れることで、動作をゆっくり確認できます。
        try:
            # システムにインストールされている Google Chrome を使用しようとします
            browser = p.chromium.launch(headless=False, channel="chrome")
            print("Google Chromeを起動しました。")
        except Exception:
            # Chromeが見つからない場合は、同梱のChromiumを起動します
            print("Google Chromeが見つからないため、Chromiumを起動します。")
            browser = p.chromium.launch(headless=False)

        # 新しいタブを開く
        context = browser.new_context()
        page = context.new_page()

        # Googleのホームページへ移動
        print("Googleのホームページへ移動しています...")
        page.goto("https://www.google.com")

        print("完了しました。Googleのホームページを表示中です。")
        print("※ このプログラムを終了するか、ブラウザを閉じると終了します。")

        # ブラウザが閉じられるまで待機する仕組み
        # 本来はGUIアプリ等に組み込むのが一般的ですが、
        # 簡易アプリとしてスクリプトを維持するために無限ループを使用します。
        browser.on("disconnected", lambda _: sys.exit())

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nプログラムを終了します。")
            browser.close()

if __name__ == "__main__":
    launch_chrome_and_google()
