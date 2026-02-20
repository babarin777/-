# Windows環境でPython未インストールの場合は run_news_gadget.bat を使用してください。
import tkinter as tk
from tkinter import ttk, messagebox
import sys

# 依存ライブラリのチェック
try:
    import feedparser
    import requests
except ImportError:
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
from urllib.parse import quote_plus

# 1. ニュース分野と背景色の設定
CATEGORIES = [
    {"label": "AI関連", "q": "人工知能 OR 生成AI OR AI", "color": "#F0F8FF"}, # AliceBlue
    {"label": "再エネ", "q": "再生可能エネルギー OR 再エネ OR 太陽光 OR 風力", "color": "#FFF0F5"}, # LavenderBlush
    {"label": "EV", "q": "電気自動車 OR EV OR テスラ OR 自動運転", "color": "#F0FFF0"}    # Honeydew
]

MAIN_FONT = ("Meiryo UI", 10)
TITLE_FONT = ("Meiryo UI", 11, "bold")
SMALL_FONT = ("Meiryo UI", 8)

class TabbedNewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("News Gadget")
        self.root.geometry("500x700")

        # セッションとクッキーの設定（Googleの同意画面回避）
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://news.google.com/"
        })
        self.session.cookies.set("CONSENT", "YES+", domain=".google.com")

        # フォント設定
        self.default_font = MAIN_FONT

        # --- ヘッダー ---
        header = tk.Frame(root)
        header.pack(fill="x", pady=10)

        self.btn_refresh = tk.Button(header, text="ニュースを更新", command=self.refresh, font=TITLE_FONT)
        self.btn_refresh.pack()

        # --- タブ制御 (ttk.Notebook) ---
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=MAIN_FONT, padding=[10, 5])

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabs = {}
        for cat in CATEGORIES:
            tab_frame = tk.Frame(self.notebook, bg=cat["color"])
            self.notebook.add(tab_frame, text=cat["label"])

            # 各タブ内にスクロールエリアを作成
            canvas = tk.Canvas(tab_frame, bg=cat["color"], highlightthickness=0)
            scrollbar = tk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
            content_frame = tk.Frame(canvas, bg=cat["color"])

            content_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )

            canvas_window = canvas.create_window((0, 0), window=content_frame, anchor="nw", width=460)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            self.tabs[cat["label"]] = {
                "content": content_frame,
                "canvas": canvas,
                "color": cat["color"]
            }

        # --- ヘルプ表示 ---
        help_text = "※表示されない場合はネット接続を確認してください"
        tk.Label(root, text=help_text, font=SMALL_FONT, fg="gray").pack(fill="x", pady=2)

        self.refresh()

    def refresh(self):
        # 全タブを読み込み中に
        for cat_label, tab in self.tabs.items():
            for widget in tab["content"].winfo_children():
                widget.destroy()
            tk.Label(tab["content"], text="取得中...", bg=tab["color"], font=MAIN_FONT).pack(pady=50)

        # 別スレッドでニュース取得
        threading.Thread(target=self.fetch_all, daemon=True).start()

    def fetch_all(self):
        for cat in CATEGORIES:
            items = self.fetch_news(cat["q"])
            # 各カテゴリごとにメインスレッドで描画
            self.root.after(0, self.display_category, cat["label"], items)

    def fetch_news(self, query):
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=ja&gl=JP&ceid=JP:ja"
        try:
            try:
                r = self.session.get(url, timeout=15)
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
                # SSLエラーや接続エラー時の回避策
                r = self.session.get(url, timeout=15, verify=False)

            if r.status_code != 200:
                print(f"Fetch Error ({query}): HTTP {r.status_code}")
                return []

            feed = feedparser.parse(r.content)

            # 全記事を日付順（新しい順）にソート
            all_entries = sorted(feed.entries, key=lambda e: e.get("published_parsed"), reverse=True)

            # 日経新聞の記事とそれ以外を分離
            nikkei_entries = [e for e in all_entries if "日本経済新聞" in e.get("source", {}).get("title", "")]
            other_entries = [e for e in all_entries if "日本経済新聞" not in e.get("source", {}).get("title", "")]

            # 日経新聞は上位3件までを優先枠とし、残りは日付順で混ぜる
            priority_nikkei = nikkei_entries[:3]
            remaining_entries = sorted(nikkei_entries[3:] + other_entries,
                                       key=lambda e: e.get("published_parsed") or (0,),
                                       reverse=True)

            # 優先枠 + 残りを結合して上位20件を返す
            final_entries = (priority_nikkei + remaining_entries)[:20]

            return final_entries
        except Exception as e:
            print(f"Error fetching {query}: {e}")
            return []

    def display_category(self, label, items):
        tab = self.tabs[label]
        for widget in tab["content"].winfo_children():
            widget.destroy()

        if not items:
            tk.Label(tab["content"], text="記事を取得できませんでした", bg=tab["color"], font=MAIN_FONT).pack(pady=50)
            return

        for item in items:
            # 記事カード
            card = tk.Frame(tab["content"], bg="white", bd=1, relief="ridge", pady=8, padx=12)
            card.pack(fill="x", padx=10, pady=5)

            source_name = item.get("source", {}).get("title", "不明")
            is_nikkei = "日本経済新聞" in source_name

            # 日経新聞の場合はバッジを表示
            if is_nikkei:
                badge = tk.Label(card, text="日経新聞", bg="#003399", fg="white", font=SMALL_FONT, padx=4)
                badge.pack(anchor="w", pady=(0, 2))

            # タイトル
            title_color = "#0000EE" if not is_nikkei else "#000000"
            title = tk.Label(card, text=item.title, wraplength=400, justify="left",
                            bg="white", fg=title_color, cursor="hand2", font=TITLE_FONT)
            title.pack(anchor="w")
            title.bind("<Button-1>", lambda e, url=item.link: webbrowser.open(url))

            # 下線エフェクト (マウスホバー時)
            title.bind("<Enter>", lambda e, t=title: t.configure(font=("Meiryo UI", 11, "bold", "underline")))
            title.bind("<Leave>", lambda e, t=title: t.configure(font=TITLE_FONT))

            # 情報
            pub_date = item.get('published', '')
            info = f"{source_name} | {pub_date}"
            tk.Label(card, text=info, font=SMALL_FONT, bg="white", fg="gray").pack(anchor="w", pady=(2, 0))

        # スクロール領域の更新
        tab["canvas"].configure(scrollregion=tab["canvas"].bbox("all"))

if __name__ == "__main__":
    root = tk.Tk()
    app = TabbedNewsGadget(root)
    root.mainloop()
