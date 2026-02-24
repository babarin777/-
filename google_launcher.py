import webbrowser
import tkinter as tk
from tkinter import messagebox
import os
import sys

def open_google():
    """
    Googleのホームページをブラウザで開きます。
    可能な限り Google Chrome を優先して使用します。
    """
    url = "https://www.google.com"
    try:
        # Windows環境でGoogle Chromeのインストールパスを直接探す
        if sys.platform == "win32":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    # Chromeを登録して使用する
                    chrome_id = 'chrome'
                    webbrowser.register(chrome_id, None, webbrowser.BackgroundBrowser(path))
                    webbrowser.get(chrome_id).open(url)
                    return True

        # Chromeが見つからない場合やWindows以外は、システムのデフォルトブラウザを使用
        # これにより、追加のライブラリ（Playwright等）なしで確実に動作します
        webbrowser.open(url)
        return True
    except Exception as e:
        return str(e)

def main():
    # 1. 起動時に自動でGoogleを開く
    print("ブラウザを起動しています...")
    result = open_google()

    # 2. 簡易的なGUIを表示（動作の確認と、失敗時の通知用）
    # TkinterはPython標準ライブラリなので、追加インストール不要です
    try:
        root = tk.Tk()
        root.title("Google起動アプリ")
        root.geometry("350x180")

        # ウィンドウを画面中央付近に表示
        root.eval('tk::PlaceWindow . center')

        msg = "ブラウザでGoogleを開きました。" if result is True else f"エラーが発生しました:\n{result}"
        color = "black" if result is True else "red"

        label = tk.Label(root, text=msg, fg=color, pady=20, wraplength=300)
        label.pack()

        # ボタンエリア
        frame = tk.Frame(root)
        frame.pack(pady=10)

        btn_retry = tk.Button(frame, text="もう一度Googleを開く", command=open_google, width=20)
        btn_retry.pack(pady=5)

        btn_exit = tk.Button(frame, text="閉じる", command=root.destroy, width=20)
        btn_exit.pack(pady=5)

        # 常に最前面に表示
        root.attributes("-topmost", True)

        print("アプリが起動しました。")
        root.mainloop()

    except Exception as e:
        # 万が一GUIが起動できない環境（LinuxのCUI環境など）の場合
        print(f"GUIの起動に失敗しました。ブラウザ起動結果: {result}")
        if result is not True:
            print(f"エラー詳細: {result}")

if __name__ == "__main__":
    main()
