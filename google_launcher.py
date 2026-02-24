import sys
import time
import traceback
from playwright.sync_api import sync_playwright, Error as PlaywrightError

def launch_chrome_and_google():
    """
    Playwrightを使用してChromeを自動的に起動し、Googleのホームページを表示します。
    エラーハンドリングを強化し、問題発生時に詳細を表示します。
    """
    print("--- Google Launcher 起動中 ---")

    with sync_playwright() as p:
        browser = None
        try:
            print("ブラウザを起動しています...")
            try:
                # システムの Google Chrome を優先
                browser = p.chromium.launch(headless=False, channel="chrome")
                print("Google Chrome を起動しました。")
            except Exception as e:
                print(f"Google Chrome の起動に失敗しました: {e}")
                print("同梱の Chromium で再試行します...")
                browser = p.chromium.launch(headless=False)
                print("Chromium を起動しました。")

            # コンテキストとページの作成
            context = browser.new_context()
            page = context.new_page()

            # タイムアウト設定（30秒）
            page.set_default_timeout(30000)

            print("Googleのホームページ (https://www.google.com) へ移動しています...")
            response = page.goto("https://www.google.com")

            if response:
                print(f"ステータスコード: {response.status}")
                if response.ok:
                    print("正常にページが表示されました。")
                else:
                    print(f"警告: ページは読み込まれましたが、ステータスが OK ではありません。")
            else:
                print("エラー: レスポンスを受信できませんでした。")

            print("\n完了しました。Googleのホームページを表示中です。")
            print("※ ブラウザを閉じるか、この画面で Ctrl+C を押すと終了します。")

            # ブラウザが閉じられた時の処理
            browser.on("disconnected", lambda _: sys.exit())

            # ユーザーが終了するまで待機
            while True:
                time.sleep(1)

        except PlaywrightError as e:
            print("\n[Playwrightエラーが発生しました]")
            print(f"内容: {e}")
            # GUIがない環境（サーバー等）で実行しようとした場合などのエラーコード的な役割
            if "Target page, context or browser has been closed" in str(e):
                print("ブラウザが予期せず閉じられました。")
        except Exception as e:
            print("\n[予期しないエラーが発生しました]")
            print(f"エラー種別: {type(e).__name__}")
            print(f"エラー内容: {e}")
            print("\n詳細なスタックトレース:")
            traceback.print_exc()
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass
            print("\nプログラムを終了します。Enterキーを押すとこの画面を閉じます。")
            input() # エラーメッセージを確認できるように一時停止

if __name__ == "__main__":
    launch_chrome_and_google()
