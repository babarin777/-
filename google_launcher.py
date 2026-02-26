import tkinter as tk
from tkinter import ttk
import webbrowser
import os
import sys
import requests
import feedparser
import threading
import urllib.parse
from datetime import datetime

# --- 設定 ---
CATEGORIES = [
    {"name": "AI関連", "query": "人工知能 OR 生成AI OR AI", "bg": "AliceBlue"},
    {"name": "再エネ", "query": "再生可能エネルギー OR 太陽光発電 OR 風力発電", "bg": "LavenderBlush"},
    {"name": "EV", "query": "電気自動車 OR EV OR リチウムイオン電池", "bg": "Honeydew"}
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def open_in_chrome(url):
    """可能な限り Google Chrome を優先してURLを開きます。"""
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
        webbrowser.open(url)
    except:
        webbrowser.open(url)

class SimpleNewsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Google ニュースピックアップ")
        self.root.geometry("500x750")

        # スクロールエリアの作成
        self.canvas = tk.Canvas(root)
        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=480)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 操作パネル
        control_panel = tk.Frame(root)
        control_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.refresh_btn = tk.Button(control_panel, text="ニュースを更新", command=self.refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(control_panel, text="準備完了", fg="gray")
        self.status_label.pack(side=tk.RIGHT, padx=5)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # マウスホイール対応
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.refresh()

    def refresh(self):
        self.status_label.config(text="取得中...", fg="blue")
        self.refresh_btn.config(state=tk.DISABLED)
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        threading.Thread(target=self.load_news, daemon=True).start()

    def load_news(self):
        for cat in CATEGORIES:
            articles = self.fetch_news(cat["query"])
            self.root.after(0, self.add_section, cat["name"], cat["bg"], articles)

        self.root.after(0, lambda: self.status_label.config(text=f"最終更新: {datetime.now().strftime('%H:%M')}", fg="gray"))
        self.root.after(0, lambda: self.refresh_btn.config(state=tk.NORMAL))

    def fetch_news(self, query):
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            feed = feedparser.parse(resp.text)

            # 日経優先ロジック (上位3件)
            nikkei = [e for e in feed.entries if "日本経済新聞" in e.source.get('title', '') or "nikkei" in e.link.lower()]
            others = [e for e in feed.entries if e not in nikkei]

            return (nikkei[:3] + others)[:8] # 各分野8件程度表示
        except:
            return []

    def add_section(self, name, bg, articles):
        # 見出し
        header = tk.Label(self.scrollable_frame, text=f"■ {name}", bg=bg, font=("Meiryo UI", 12, "bold"), anchor="w", padx=10, pady=5)
        header.pack(fill=tk.X)

        section_frame = tk.Frame(self.scrollable_frame, bg=bg, padx=10, pady=5)
        section_frame.pack(fill=tk.X)

        if not articles:
            tk.Label(section_frame, text="取得できませんでした", bg=bg, fg="red").pack(anchor="w")

        for a in articles:
            is_nikkei = "日本経済新聞" in a.source.get('title', '') or "nikkei" in a.link.lower()
            title = ("★ " if is_nikkei else "・ ") + a.title

            lbl = tk.Label(section_frame, text=title, bg=bg, fg="blue", cursor="hand2",
                           wraplength=440, justify=tk.LEFT, font=("Meiryo UI", 9, "underline"))
            lbl.pack(anchor="w", pady=2)
            lbl.bind("<Button-1>", lambda e, url=a.link: open_in_chrome(url))

            source = tk.Label(section_frame, text=f"   {a.source.get('title', '不明')}", bg=bg, fg="gray", font=("Meiryo UI", 8))
            source.pack(anchor="w", pady=(0, 5))

        # 区切り
        tk.Frame(self.scrollable_frame, height=10).pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleNewsApp(root)
    root.mainloop()
