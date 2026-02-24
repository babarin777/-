import tkinter as tk
from tkinter import ttk
import webbrowser
import os
import sys
import requests
import feedparser
import threading
import time
from datetime import datetime
import urllib.parse

# --- 設定 ---
CATEGORIES = {
    "AI関連": {
        "query": "人工知能 OR 生成AI OR AI OR ChatGPT",
        "bg_color": "AliceBlue",
        "id": "ai"
    },
    "再エネ": {
        "query": "再生可能エネルギー OR 太陽光発電 OR 風力発電 OR 脱炭素",
        "bg_color": "LavenderBlush",
        "id": "renewable"
    },
    "EV": {
        "query": "電気自動車 OR EV OR リチウムイオン電池 OR 全固体電池",
        "bg_color": "Honeydew",
        "id": "ev"
    }
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("最新ニュースガジェット (AI・再エネ・EV)")
        self.root.geometry("600x700")

        self.stay_on_top = tk.BooleanVar(value=False)

        self.setup_ui()
        self.refresh_news()

    def setup_ui(self):
        # メニュー/操作エリア
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        self.refresh_btn = tk.Button(top_frame, text="更新", command=self.refresh_news)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.on_top_check = tk.Checkbutton(top_frame, text="最前面に表示", variable=self.stay_on_top, command=self.toggle_on_top)
        self.on_top_check.pack(side=tk.RIGHT, padx=5)

        # タブエリア
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tabs = {}
        for name, info in CATEGORIES.items():
            tab = tk.Frame(self.notebook, bg=info["bg_color"])
            self.notebook.add(tab, text=name)

            # スクロール可能なエリア
            canvas = tk.Canvas(tab, bg=info["bg_color"], highlightthickness=0)
            scrollbar = tk.Scrollbar(tab, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=info["bg_color"])

            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # マウスホイールでスクロール
            def _make_mousewheel_handler(c):
                return lambda event: c.yview_scroll(int(-1*(event.delta/120)), "units")

            handler = _make_mousewheel_handler(canvas)
            canvas.bind("<Enter>", lambda e, h=handler: canvas.bind_all("<MouseWheel>", h))
            canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

            self.tabs[name] = {
                "frame": scrollable_frame,
                "canvas": canvas
            }

        # ヘルプ/ステータス
        self.status_label = tk.Label(self.root, text="読み込み中...", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def toggle_on_top(self):
        self.root.attributes("-topmost", self.stay_on_top.get())

    def open_in_chrome(self, url):
        """
        可能な限り Google Chrome を優先してURLを開きます。
        """
        try:
            if sys.platform == "win32":
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
                ]
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_id = 'chrome'
                        webbrowser.register(chrome_id, None, webbrowser.BackgroundBrowser(path))
                        webbrowser.get(chrome_id).open(url)
                        return

            # Chromeが見つからない場合はデフォルトブラウザ
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening browser: {e}")
            webbrowser.open(url)

    def refresh_news(self):
        self.status_label.config(text="ニュースを取得中...")
        self.refresh_btn.config(state=tk.DISABLED)

        # 既存のコンテンツをクリア
        for tab_info in self.tabs.values():
            for widget in tab_info["frame"].winfo_children():
                widget.destroy()

        # 非同期で取得
        threading.Thread(target=self.fetch_all_categories, daemon=True).start()

    def fetch_all_categories(self):
        for name, info in CATEGORIES.items():
            articles = self.fetch_news(info["query"])
            # GUI更新はメインスレッドで
            self.root.after(0, self.display_news, name, articles)

        self.root.after(0, lambda: self.status_label.config(text=f"最終更新: {datetime.now().strftime('%H:%M:%S')}"))
        self.root.after(0, lambda: self.refresh_btn.config(state=tk.NORMAL))

    def fetch_news(self, query):
        encoded_query = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        headers = {"User-Agent": USER_AGENT}
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            entries = feed.entries

            # 日経関連を優先するロジック
            # 1. 日経の記事を抽出
            nikkei_articles = [e for e in entries if "日本経済新聞" in e.source.get('title', '') or "nikkei" in e.link.lower()]
            other_articles = [e for e in entries if e not in nikkei_articles]

            # 2. 日経の上位3つを先頭に
            priority_nikkei = nikkei_articles[:3]
            remaining_nikkei = nikkei_articles[3:]

            # 3. 残りは日付順にソート（Google News RSSは概ね日付順だが念のため）
            remaining = remaining_nikkei + other_articles
            # 日付パース
            def get_date(entry):
                try:
                    return time.mktime(entry.published_parsed)
                except:
                    return 0

            remaining.sort(key=get_date, reverse=True)

            return (priority_nikkei + remaining)[:20] # 最大20件

        except Exception as e:
            print(f"Error fetching news for {query}: {e}")
            return []

    def display_news(self, category_name, articles):
        frame = self.tabs[category_name]["frame"]
        bg = CATEGORIES[category_name]["bg_color"]

        if not articles:
            tk.Label(frame, text="記事が見つかりませんでした。ネットワークを確認してください。", bg=bg, fg="red", padx=10, pady=10).pack()
            return

        for article in articles:
            # 記事枠
            card = tk.Frame(frame, bg=bg, bd=1, relief=tk.RIDGE, padx=8, pady=8)
            card.pack(fill=tk.X, padx=5, pady=3)

            # 日経新聞フラグ
            is_nikkei = "日本経済新聞" in article.source.get('title', '') or "nikkei" in article.link.lower()
            source_text = f"[{article.source.get('title', '不明')}]"
            if is_nikkei:
                source_text = "★ " + source_text

            # タイトル
            title_label = tk.Label(card, text=article.title, bg=bg, fg="blue", cursor="hand2",
                                  font=("Meiryo UI", 10, "bold" if is_nikkei else "normal"),
                                  wraplength=520, justify=tk.LEFT)
            title_label.pack(anchor=tk.W)

            # クリックイベント
            title_label.bind("<Button-1>", lambda e, url=article.link: self.open_in_chrome(url))

            # 情報（ソース・日付）
            info_text = f"{source_text} - {article.published}"
            info_label = tk.Label(card, text=info_text, bg=bg, fg="gray", font=("Meiryo UI", 8))
            info_label.pack(anchor=tk.W)

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsGadget(root)
    root.mainloop()
