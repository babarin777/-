import tkinter as tk
from tkinter import ttk, messagebox
import sys
import threading
import webbrowser
import os
from urllib.parse import quote_plus
import urllib3

# SSL警告を非表示にする（社内網対策の verify=False 用）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. 依存ライブラリのチェック ---
try:
    import feedparser
    import requests
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "実行エラー",
        "必要なライブラリが見つかりません。\n\n"
        "コマンドプロンプトを開き、以下のコマンドを【一文字ずつ正確に】入力して実行してください：\n\n"
        "py -m pip install requests feedparser"
    )
    sys.exit(1)

# --- 2. 設定：ニュース分野と背景色 ---
CATEGORIES = [
    {"label": "AI関連", "q": "AI OR 人工知能", "color": "#F0F8FF"}, # AliceBlue
    {"label": "再エネ", "q": "再生可能エネルギー OR 再エネ", "color": "#FFF0F5"}, # LavenderBlush
    {"label": "EV", "q": "電気自動車 OR EV", "color": "#F0FFF0"}    # Honeydew
]

# フォント設定
FONT_FAMILY = "Meiryo UI"
MAIN_FONT = (FONT_FAMILY, 10)
TITLE_FONT = (FONT_FAMILY, 11, "bold")
SMALL_FONT = (FONT_FAMILY, 8)

class RobustNewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("News Gadget")
        self.root.geometry("500x750")

        # セッションとクッキーの設定（Google同意画面・社内網対策）
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://news.google.com/"
        })
        self.session.cookies.set("CONSENT", "YES+", domain=".google.com")

        # --- UI構築 ---
        header = tk.Frame(root)
        header.pack(fill="x", pady=10)

        tk.Button(header, text="最新ニュースに更新", command=self.refresh,
                  font=TITLE_FONT, bg="#f0f0f0", padx=20).pack()

        # タブデザインの設定
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=MAIN_FONT, padding=[10, 5])

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabs = {}
        for cat in CATEGORIES:
            tab_frame = tk.Frame(self.notebook, bg=cat["color"])
            self.notebook.add(tab_frame, text=cat["label"])

            # 各タブ内のスクロール設定
            canvas = tk.Canvas(tab_frame, bg=cat["color"], highlightthickness=0)
            scrollbar = tk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
            content = tk.Frame(canvas, bg=cat["color"])

            content.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))
            canvas.create_window((0, 0), window=content, anchor="nw", width=460)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.tabs[cat["label"]] = {"frame": content, "canvas": canvas, "color": cat["color"]}

        tk.Label(root, text="※表示されない場合はネットワーク設定を確認してください",
                 font=SMALL_FONT, fg="gray").pack(fill="x", pady=2)

        self.refresh()

    def refresh(self):
        """全タブを読み込み状態にする"""
        for label, tab in self.tabs.items():
            for w in tab["frame"].winfo_children(): w.destroy()
            tk.Label(tab["frame"], text="読み込み中...", bg=tab["color"], font=MAIN_FONT).pack(pady=50)

        # 非同期で取得開始
        threading.Thread(target=self.fetch_all, daemon=True).start()

    def fetch_all(self):
        """全カテゴリを順番に取得して描画"""
        for cat in CATEGORIES:
            items = self.fetch_news(cat["q"])
            self.root.after(0, self.display_category, cat["label"], items)

    def fetch_news(self, query):
        """GoogleニュースRSSから取得（SSL/プロキシ対策込み）"""
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            try:
                # まずは標準の接続を試行
                r = self.session.get(url, timeout=15)
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                # 失敗した場合はSSL検証をスキップして再試行
                r = self.session.get(url, timeout=15, verify=False)

            if r.status_code != 200:
                self._last_error = f"HTTPエラー {r.status_code}"
                return []

            # 受信内容のデバッグ用
            content = r.text
            if not content.strip():
                self._last_error = "受信内容が空です。"
                return []

            # フィルタリングチェック
            if "<html" in content.lower()[:200]:
                if "consent.google.com" in r.url:
                    self._last_error = "Googleの同意画面にブロックされました。クッキー設定を確認してください。"
                else:
                    self._last_error = "社内フィルタ等によりブロックされた可能性があります。"
                return []

            feed = feedparser.parse(r.content)

            if not feed.entries:
                snippet = content[:100].replace('\n', ' ')
                self._last_error = f"記事が見つかりません。 (内容: {snippet}...)"
                return []

            # --- ソートロジック ---
            # 1. 全記事を日付順に並める
            all_items = sorted(feed.entries, key=lambda e: e.get("published_parsed") or (0,), reverse=True)
            # 2. 日経関連とそれ以外を分ける
            nikkei = [e for e in all_items if "日本経済新聞" in e.get("source", {}).get("title", "")]
            others = [e for e in all_items if "日本経済新聞" not in e.get("source", {}).get("title", "")]
            # 3. 日経上位3件を優先枠とし、残りは日付順で統合
            final = (nikkei[:3] + sorted(nikkei[3:] + others,
                                        key=lambda e: e.get("published_parsed") or (0,),
                                        reverse=True))[:20]
            return final
        except:
            return []

    def display_category(self, label, items):
        """UIに記事カードを並べる"""
        tab = self.tabs[label]
        for w in tab["frame"].winfo_children(): w.destroy()

        if not items:
            error_msg = "記事が見つかりませんでした"
            if hasattr(self, '_last_error'):
                error_msg += f"\n\n詳細: {self._last_error}"

            tk.Label(tab["frame"], text=error_msg, bg=tab["color"], font=MAIN_FONT, justify="center").pack(pady=50)
            return

        for item in items:
            card = tk.Frame(tab["frame"], bg="white", bd=1, relief="ridge", pady=10, padx=15)
            card.pack(fill="x", padx=10, pady=5)

            source = item.get("source", {}).get("title", "不明")
            if "日本経済新聞" in source:
                tk.Label(card, text="日経新聞", bg="#003399", fg="white", font=SMALL_FONT, padx=5).pack(anchor="w", pady=(0,5))

            title = tk.Label(card, text=item.title, wraplength=400, justify="left",
                            bg="white", fg="#0000EE", cursor="hand2", font=TITLE_FONT)
            title.pack(anchor="w")
            title.bind("<Button-1>", lambda e, url=item.link: webbrowser.open(url))
            # ホバーエフェクト
            title.bind("<Enter>", lambda e, t=title: t.configure(font=(FONT_FAMILY, 11, "bold", "underline")))
            title.bind("<Leave>", lambda e, t=title: t.configure(font=TITLE_FONT))

            tk.Label(card, text=f"{source} | {item.get('published', '')}",
                     font=SMALL_FONT, bg="white", fg="gray").pack(anchor="w", pady=(5,0))

        tab["canvas"].configure(scrollregion=tab["canvas"].bbox("all"))

if __name__ == "__main__":
    root = tk.Tk()
    app = RobustNewsGadget(root)
    root.mainloop()
