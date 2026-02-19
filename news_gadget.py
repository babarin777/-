import sys

# 依存ライブラリのチェック
missing_libs = []
try: import requests
except ImportError: missing_libs.append("requests")
try: import feedparser
except ImportError: missing_libs.append("feedparser")
try: from PIL import Image, ImageTk
except ImportError: missing_libs.append("Pillow (PIL)")

if missing_libs:
    print(f"エラー: 以下のライブラリがインストールされていません: {', '.join(missing_libs)}")
    print("インストールするには以下のコマンドを実行してください:")
    print(f"pip install {' '.join(['requests', 'feedparser', 'Pillow'])}")
    sys.exit(1)

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import threading
import re
import html as html_lib
import urllib.parse
from io import BytesIO
from PIL import Image, ImageTk
import logging

# --- デザイン設定 ---
COLOR_BG = "#F1F8E9"        # パステルグリーン背景
COLOR_HEADER = "#C8E6C9"    # ヘッダー
COLOR_CARD = "#FFFFFF"      # カード背景
COLOR_TEXT_MAIN = "#2E7D32" # 濃いグリーン
COLOR_TEXT_SUB = "#546E7A"  # サブテキスト
COLOR_ACCENT = "#81C784"    # アクセントグリーン
COLOR_BORDER = "#DCEDC8"    # 境界線
COLOR_VIDEO_TAG = "#FF5252" # ビデオタグ用

FONT_S = ("Yu Gothic UI", 9)
FONT_M = ("Yu Gothic UI", 11)
FONT_B = ("Yu Gothic UI", 12, "bold")
FONT_TITLE = ("Impact", 28)

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsCard(tk.Frame):
    def __init__(self, parent, title, link, date, source, image_obj=None, is_video=False):
        super().__init__(parent, bg=COLOR_CARD, bd=1, relief=tk.FLAT, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.link = link

        # マウスイベントのバインド
        for widget in [self]:
            widget.bind("<Button-1>", self.open_link)
            widget.bind("<Enter>", self.on_enter)
            widget.bind("<Leave>", self.on_leave)

        # 内容の配置
        inner = tk.Frame(self, bg=COLOR_CARD, padx=15, pady=15)
        inner.pack(fill=tk.BOTH, expand=True)
        inner.bind("<Button-1>", self.open_link)

        # 画像
        if image_obj:
            img_label = tk.Label(inner, image=image_obj, bg=COLOR_CARD)
            img_label.image = image_obj # 参照保持
            img_label.pack(fill=tk.X, pady=(0, 10))
            img_label.bind("<Button-1>", self.open_link)

        # タグ（動画など）
        if is_video:
            tag_frame = tk.Frame(inner, bg=COLOR_VIDEO_TAG, padx=5, pady=2)
            tag_frame.pack(anchor=tk.W, pady=(0, 5))
            tk.Label(tag_frame, text="VIDEO 🎬", fg="white", bg=COLOR_VIDEO_TAG, font=("Yu Gothic UI", 8, "bold")).pack()

        # ソースと日付
        meta_text = f"{source} • {date}"
        tk.Label(inner, text=meta_text, fg=COLOR_TEXT_SUB, bg=COLOR_CARD, font=FONT_S).pack(anchor=tk.W)

        # タイトル
        t_label = tk.Label(inner, text=title, fg=COLOR_TEXT_MAIN, bg=COLOR_CARD, font=FONT_B,
                           wraplength=600, justify=tk.LEFT, cursor="hand2")
        t_label.pack(anchor=tk.W, pady=(5, 0))
        t_label.bind("<Button-1>", self.open_link)

    def open_link(self, event=None):
        webbrowser.open(self.link)

    def on_enter(self, event=None):
        self.config(bg="#F9FBE7")
        for child in self.winfo_children():
            child.config(bg="#F9FBE7")
            for subchild in child.winfo_children():
                if subchild.winfo_class() == 'Frame':
                    continue
                subchild.config(bg="#F9FBE7")

    def on_leave(self, event=None):
        self.config(bg=COLOR_CARD)
        for child in self.winfo_children():
            child.config(bg=COLOR_CARD)
            for subchild in child.winfo_children():
                if subchild.winfo_class() == 'Frame' and subchild.cget("bg") == COLOR_VIDEO_TAG:
                    continue
                subchild.config(bg=COLOR_CARD)

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Visual Trend Explorer v3")
        self.root.geometry("1100x900")
        self.root.configure(bg=COLOR_BG)

        self.categories = [
            {"id": "ai", "name": "AI・人工知能 🤖", "query": "AI OR 人工知能"},
            {"id": "re", "name": "再生可能エネルギー 🌱", "query": "再生可能エネルギー OR 再エネ"},
            {"id": "ev", "name": "電気自動車・EV 🚗", "query": "EV OR 電気自動車"},
            {"id": "video", "name": "最新動画・映像 🎬", "query": "(AI OR 再エネ OR EV) (動画 OR 映像 OR YouTube)"}
        ]

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        self.setup_ui()
        self.check_connection_and_start()

    def check_connection_and_start(self):
        def check():
            self.status_var.set("接続確認中...")
            try:
                requests.get("https://www.google.com", timeout=5)
                self.root.after(0, self.refresh_all)
            except Exception:
                self.root.after(0, lambda: self.status_var.set("接続エラー: インターネットを確認してください"))
                logging.error("No internet connection.")

        threading.Thread(target=check, daemon=True).start()

    def setup_ui(self):
        # メインコンテナ
        self.main_frame = tk.Frame(self.root, bg=COLOR_BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # ヘッダー
        header = tk.Frame(self.main_frame, bg=COLOR_HEADER, padx=30, pady=20, bd=0)
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(header, text="TECH TRENDS", bg=COLOR_HEADER, fg=COLOR_TEXT_MAIN, font=FONT_TITLE).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(header, textvariable=self.status_var, bg=COLOR_HEADER, fg=COLOR_TEXT_SUB, font=FONT_M).pack(side=tk.LEFT, padx=30)

        btn = tk.Button(header, text="🔄 更新", command=self.refresh_all, bg=COLOR_ACCENT, fg="white",
                        font=FONT_B, relief=tk.FLAT, padx=20, pady=5, cursor="hand2")
        btn.pack(side=tk.RIGHT)

        # タブ
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.scroll_containers = {}

        for cat in self.categories:
            cat_id = cat["id"]

            # スクロール可能な領域の作成
            outer_frame = tk.Frame(self.notebook, bg=COLOR_BG)
            self.notebook.add(outer_frame, text=cat["name"])

            canvas = tk.Canvas(outer_frame, bg=COLOR_BG, highlightthickness=0)
            scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=COLOR_BG)

            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=1040)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # マウスホイール対応 (キャンバスに入った時のみ有効化)
            def _bind_mousewheel(event, c=canvas):
                c.bind_all("<MouseWheel>", lambda e: c.yview_scroll(int(-1*(e.delta/120)), "units"))
            def _unbind_mousewheel(event, c=canvas):
                c.unbind_all("<MouseWheel>")

            canvas.bind("<Enter>", _bind_mousewheel)
            canvas.bind("<Leave>", _unbind_mousewheel)

            self.scroll_containers[cat_id] = scrollable_frame

    def refresh_all(self):
        self.status_var.set("更新中...")
        for cat in self.categories:
            threading.Thread(target=self.fetch_category, args=(cat,), daemon=True).start()

    def fetch_category(self, cat):
        cat_id = cat["id"]
        query = cat["query"]

        # 既存コンテンツの削除
        for widget in self.scroll_containers[cat_id].winfo_children():
            widget.destroy()

        tk.Label(self.scroll_containers[cat_id], text="読み込み中...", bg=COLOR_BG, fg=COLOR_TEXT_SUB, font=FONT_M, pady=20).pack()

        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.root.after(0, self.show_empty, cat_id)
                return

            # 上位5件のみ画像取得（負荷軽減）
            entries_to_process = feed.entries[:10]

            processed_data = []
            for entry in entries_to_process:
                img_obj = None
                # トップ2件のみ画像を試みる
                if feed.entries.index(entry) < 3:
                    img_obj = self.get_og_image(entry.link)

                processed_data.append({
                    "title": entry.title,
                    "link": entry.link,
                    "date": entry.published if hasattr(entry, 'published') else "",
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "image": img_obj,
                    "is_video": any(kw in entry.title for kw in ["動画", "映像", "YouTube", "配信"])
                })

            self.root.after(0, self.update_ui, cat_id, processed_data)

        except Exception as e:
            logging.error(f"Error fetching {cat_id}: {e}")
            self.root.after(0, self.show_error, cat_id, str(e))

    def get_og_image(self, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=5)
            html = res.text
            match = re.search(r'<meta [^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html)

            if match:
                img_url = html_lib.unescape(match.group(1))
                # 相対パス対応
                if img_url.startswith('//'): img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed = urllib.parse.urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"

                img_res = requests.get(img_url, headers=self.headers, timeout=5)
                img = Image.open(BytesIO(img_res.content))
                img.thumbnail((800, 400))
                return img # PhotoImageではなくImageオブジェクトを返す
        except:
            pass
        return None

    def update_ui(self, cat_id, data):
        container = self.scroll_containers[cat_id]
        for widget in container.winfo_children():
            widget.destroy()

        for item in data:
            # メインスレッドでPhotoImageに変換
            photo = None
            if item["image"]:
                try:
                    photo = ImageTk.PhotoImage(item["image"])
                except Exception as e:
                    logging.error(f"Error creating PhotoImage: {e}")

            card = NewsCard(container, item["title"], item["link"], item["date"],
                            item["source"], photo, item["is_video"])
            card.pack(fill=tk.X, padx=20, pady=10)

        self.status_var.set("完了")

    def show_empty(self, cat_id):
        container = self.scroll_containers[cat_id]
        for widget in container.winfo_children():
            widget.destroy()
        tk.Label(container, text="記事が見つかりませんでした。", bg=COLOR_BG, fg=COLOR_TEXT_SUB, font=FONT_M, pady=20).pack()
        self.status_var.set("完了（データなし）")

    def show_error(self, cat_id, error_msg):
        container = self.scroll_containers[cat_id]
        for widget in container.winfo_children():
            widget.destroy()
        tk.Label(container, text=f"エラーが発生しました:\n{error_msg}", bg=COLOR_BG, fg="red", font=FONT_M, pady=20).pack()
        self.status_var.set("エラー")

if __name__ == "__main__":
    root = tk.Tk()

    app = NewsGadget(root)
    root.mainloop()
