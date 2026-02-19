import tkinter as tk
from tkinter import messagebox
import sys

# 依存ライブラリのチェック
try:
    import feedparser
    import requests
except ImportError:
    # Tkinterは標準ライブラリなので使える前提
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "実行エラー",
        "必要なライブラリ（requests, feedparser）が見つかりません。\n\n"
        "コマンドプロンプトを開き、以下のコマンドを【一文字ずつ正確に】入力して「Enter」を押してください：\n\n"
        "py -m pip install requests feedparser\n\n"
        "※「-m」の後の「pip」を入れ忘れるとエラーになります。\n"
        "※インストール完了後、このファイルを再度実行してください。"
    )
    sys.exit(1)

import threading
import webbrowser
from urllib.parse import quote

# 1. ニュース分野と背景色の設定
CATEGORIES = [
    {"label": "AI関連", "q": "AI OR 人工知能", "color": "#F0F8FF"}, # AliceBlue
    {"label": "再エネ", "q": "再生可能エネルギー", "color": "#FFF0F5"}, # LavenderBlush
    {"label": "EV", "q": "電気自動車 OR EV", "color": "#F0FFF0"}    # Honeydew
]

class SimpleNewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("News Gadget")
        self.root.geometry("450x800")

        # --- ヘッダー ---
        self.btn_refresh = tk.Button(root, text="ニュースを更新", command=self.refresh, font=("Arial", 10, "bold"))
        self.btn_refresh.pack(pady=10)

        # --- スクロール可能なエリア ---
        self.canvas = tk.Canvas(root, bg="white")
        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="white")

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=430)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # --- ヘルプ表示 ---
        help_text = "※表示されない場合はネット接続やライブラリを確認してください"
        tk.Label(root, text=help_text, font=("Arial", 8), fg="gray", bg="white").pack(fill="x")

        self.refresh()

    def refresh(self):
        # 既存の内容をクリア
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        tk.Label(self.scroll_frame, text="取得中...", bg="white").pack(pady=20)

        # 別スレッドでニュース取得
        threading.Thread(target=self.fetch_all, daemon=True).start()

    def fetch_all(self):
        all_results = []
        for cat in CATEGORIES:
            items = self.fetch_news(cat["q"])
            all_results.append((cat, items))

        # メインスレッドで描画
        self.root.after(0, self.display, all_results)

    def fetch_news(self, query):
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            # シンプルなヘッダーでリクエスト
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
            try:
                r = requests.get(url, headers=headers, timeout=15)
            except requests.exceptions.SSLError:
                # SSLエラー時の回避策
                r = requests.get(url, headers=headers, timeout=15, verify=False)

            if r.status_code != 200: return []

            feed = feedparser.parse(r.content)
            # 3. 最新順かつ日経優先のソート
            # (日経かどうか, 日付) のタプルでソート
            sorted_entries = sorted(feed.entries, key=lambda e: (
                "日本経済新聞" in e.get("source", {}).get("title", ""),
                e.get("published_parsed")
            ), reverse=True)

            return sorted_entries[:5] # 各5件
        except:
            return []

    def display(self, all_results):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for cat, items in all_results:
            # カテゴリセクション
            section = tk.Frame(self.scroll_frame, bg=cat["color"], pady=10)
            section.pack(fill="x", pady=5)
            tk.Label(section, text=cat["label"], font=("Arial", 12, "bold"), bg=cat["color"]).pack(anchor="w", padx=10)

            if not items:
                tk.Label(section, text="取得できませんでした", bg=cat["color"]).pack(anchor="w", padx=20)
                continue

            for item in items:
                # 記事カード
                card = tk.Frame(section, bg="white", bd=1, relief="ridge", pady=8, padx=10)
                card.pack(fill="x", padx=10, pady=4)

                # タイトル（クリックでブラウザ起動）
                title = tk.Label(card, text=item.title, wraplength=380, justify="left",
                                bg="white", fg="#0000EE", cursor="hand2", font=("Arial", 10, "underline"))
                title.pack(anchor="w")
                title.bind("<Button-1>", lambda e, url=item.link: webbrowser.open(url))

                # 情報（ソース・日付）
                info = f"{item.get('source', {}).get('title', '不明')} | {item.get('published', '')}"
                tk.Label(card, text=info, font=("Arial", 8), bg="white", fg="gray").pack(anchor="w")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleNewsGadget(root)
    root.mainloop()
