import sys
import os

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
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- デザイン設定 ---
COLORS = [
    {"bg": "#E3F2FD", "header": "#BBDEFB", "accent": "#64B5F6"}, # Pale Blue
    {"bg": "#FCE4EC", "header": "#F8BBD0", "accent": "#F06292"}, # Pale Pink
    {"bg": "#F1F8E9", "header": "#DCEDC8", "accent": "#81C784"}  # Pale Green
]
COLOR_CARD = "#FFFFFF"
COLOR_TEXT_MAIN = "#37474F"
COLOR_TEXT_SUB = "#78909C"
COLOR_BORDER = "#CFD8DC"

FONT_S = ("Yu Gothic UI", 9)
FONT_M = ("Yu Gothic UI", 11)
FONT_B = ("Yu Gothic UI", 12, "bold")
FONT_TITLE = ("Yu Gothic UI", 24, "bold")

class NewsCard(tk.Frame):
    def __init__(self, parent, title, link, date, source, image_obj=None, card_bg=COLOR_CARD):
        super().__init__(parent, bg=card_bg, bd=1, relief=tk.FLAT, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.link = link
        self.card_bg = card_bg

        # マウスイベントのバインド
        self.bind("<Button-1>", self.open_link)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

        # 内容の配置
        inner = tk.Frame(self, bg=card_bg, padx=15, pady=15)
        inner.pack(fill=tk.BOTH, expand=True)
        inner.bind("<Button-1>", self.open_link)

        # 画像
        if image_obj:
            try:
                img_label = tk.Label(inner, image=image_obj, bg=card_bg)
                img_label.image = image_obj # 参照保持
                img_label.pack(fill=tk.X, pady=(0, 10))
                img_label.bind("<Button-1>", self.open_link)
            except Exception as e:
                logging.error(f"Error displaying image: {e}")

        # ソースと日付
        meta_text = f"{source} • {date}"
        meta_label = tk.Label(inner, text=meta_text, fg=COLOR_TEXT_SUB, bg=card_bg, font=FONT_S)
        meta_label.pack(anchor=tk.W)
        meta_label.bind("<Button-1>", self.open_link)

        # タイトル
        t_label = tk.Label(inner, text=title, fg=COLOR_TEXT_MAIN, bg=card_bg, font=FONT_B,
                           wraplength=800, justify=tk.LEFT, cursor="hand2")
        t_label.pack(anchor=tk.W, pady=(5, 0))
        t_label.bind("<Button-1>", self.open_link)

    def open_link(self, event=None):
        webbrowser.open(self.link)

    def on_enter(self, event=None):
        hover_bg = self.lighten_color(self.card_bg, 0.95)
        self.update_bg(hover_bg)

    def on_leave(self, event=None):
        self.update_bg(self.card_bg)

    def update_bg(self, color):
        self.config(bg=color)
        for child in self.winfo_children():
            child.config(bg=color)
            for subchild in child.winfo_children():
                subchild.config(bg=color)

    def lighten_color(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        new_rgb = [min(255, int(c + (255 - c) * (1 - factor))) for c in rgb]
        return "#%02x%02x%02x" % tuple(new_rgb)

class KeywordNewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Keyword News Gadget")
        self.root.geometry("1000x850")
        self.root.configure(bg="#F5F5F5")

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        self.setup_ui()

    def setup_ui(self):
        # メインコンテナ
        self.main_frame = tk.Frame(self.root, bg="#F5F5F5")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 入力エリア
        input_panel = tk.Frame(self.main_frame, bg="#FFFFFF", padx=15, pady=15, bd=1, relief=tk.RIDGE)
        input_panel.pack(fill=tk.X, pady=(0, 10))

        tk.Label(input_panel, text="キーワード入力 (最大3つ)", font=FONT_B, bg="#FFFFFF").pack(anchor=tk.W, pady=(0, 10))

        self.entries = []
        entry_frame = tk.Frame(input_panel, bg="#FFFFFF")
        entry_frame.pack(fill=tk.X)

        for i in range(3):
            f = tk.Frame(entry_frame, bg="#FFFFFF")
            f.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            tk.Label(f, text=f"キーワード {i+1}", font=FONT_S, bg="#FFFFFF", fg=COLOR_TEXT_SUB).pack(anchor=tk.W)
            e = tk.Entry(f, font=FONT_M, bd=1, relief=tk.SOLID)
            e.pack(fill=tk.X, pady=2)
            if i == 0: e.insert(0, "人工知能")
            if i == 1: e.insert(0, "電気自動車")
            if i == 2: e.insert(0, "半導体")
            self.entries.append(e)

        self.search_btn = tk.Button(input_panel, text="🔍 情報を取得", command=self.refresh_all,
                                   bg="#424242", fg="white", font=FONT_B, relief=tk.FLAT, padx=20, pady=5, cursor="hand2")
        self.search_btn.pack(pady=(15, 0))

        self.status_var = tk.StringVar(value="キーワードを入力して検索してください")
        tk.Label(self.main_frame, textvariable=self.status_var, font=FONT_S, bg="#F5F5F5", fg=COLOR_TEXT_SUB).pack(pady=5)

        # タブ
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.scroll_containers = []
        for i in range(3):
            color_set = COLORS[i]
            outer_frame = tk.Frame(self.notebook, bg=color_set["bg"])
            self.notebook.add(outer_frame, text=f"キーワード {i+1}")

            canvas = tk.Canvas(outer_frame, bg=color_set["bg"], highlightthickness=0)
            scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg=color_set["bg"])

            scrollable_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=950)
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # マウスホイール対応
            canvas.bind("<Enter>", lambda e, c=canvas: c.bind_all("<MouseWheel>", lambda ev: c.yview_scroll(int(-1*(ev.delta/120)), "units")))
            canvas.bind("<Leave>", lambda e, c=canvas: c.unbind_all("<MouseWheel>"))

            self.scroll_containers.append(scrollable_frame)

    def refresh_all(self):
        keywords = [e.get().strip() for e in self.entries]
        if not any(keywords):
            messagebox.showwarning("警告", "キーワードを少なくとも1つ入力してください。")
            return

        self.status_var.set("更新中...")
        for i, kw in enumerate(keywords):
            if kw:
                self.notebook.tab(i, text=kw)
                threading.Thread(target=self.fetch_keyword, args=(i, kw), daemon=True).start()
            else:
                self.notebook.tab(i, text=f"(空)")
                self.clear_container(i)

    def clear_container(self, index):
        container = self.scroll_containers[index]
        for widget in container.winfo_children():
            widget.destroy()

    def fetch_keyword(self, index, keyword):
        self.root.after(0, lambda: self.show_loading(index))

        encoded_query = urllib.parse.quote(keyword)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            logging.info(f"Fetching RSS: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            feed = feedparser.parse(response.content)

            if not feed.entries:
                logging.info(f"No entries for {keyword}")
                self.root.after(0, lambda: self.show_message(index, "記事が見つかりませんでした。"))
                return

            # 日経関連の優先順位付け
            sorted_entries = sorted(feed.entries, key=lambda e: not (
                (hasattr(e, 'source') and "日本経済新聞" in e.source.title) or
                "日経" in e.title
            ))

            # 上位20件を表示
            entries_to_process = sorted_entries[:20]

            processed_data = []
            for i, entry in enumerate(entries_to_process):
                img_obj = None
                # 上位3件のみ画像取得（レスポンス向上のため削減、タイムアウト短縮）
                if i < 3:
                    img_obj = self.get_og_image(entry.link)

                processed_data.append({
                    "title": entry.title,
                    "link": entry.link,
                    "date": getattr(entry, 'published', ""),
                    "source": entry.source.title if hasattr(entry, 'source') else "News",
                    "image": img_obj
                })

            self.root.after(0, lambda: self.update_ui(index, processed_data))

        except Exception as e:
            logging.error(f"Error fetching keyword {keyword}: {e}", exc_info=True)
            self.root.after(0, lambda: self.show_message(index, f"エラーが発生しました: {str(e)}", is_error=True))

    def show_loading(self, index):
        self.clear_container(index)
        tk.Label(self.scroll_containers[index], text="⏳ 読み込み中...",
                 bg=COLORS[index]["bg"], fg=COLOR_TEXT_SUB, font=FONT_M, pady=40).pack()

    def get_og_image(self, url):
        try:
            # タイムアウトを短縮し、リダイレクトを制限
            res = requests.get(url, headers=self.headers, timeout=3, allow_redirects=True)
            html = res.text
            match = re.search(r'<meta [^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html)

            if match:
                img_url = html_lib.unescape(match.group(1))
                if img_url.startswith('//'): img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed = urllib.parse.urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"

                img_res = requests.get(img_url, headers=self.headers, timeout=3)
                img = Image.open(BytesIO(img_res.content))
                img.thumbnail((800, 400))
                return img
        except Exception as e:
            logging.debug(f"Image fetch failed for {url}: {e}")
        return None

    def update_ui(self, index, data):
        container = self.scroll_containers[index]
        self.clear_container(index)

        for item in data:
            photo = None
            if item["image"]:
                try:
                    photo = ImageTk.PhotoImage(item["image"])
                except Exception as e:
                    logging.error(f"Error creating PhotoImage: {e}")

            card = NewsCard(container, item["title"], item["link"], item["date"],
                            item["source"], photo, card_bg=COLOR_CARD)
            card.pack(fill=tk.X, padx=20, pady=10)

        # スクロール領域の強制更新
        self.root.update_idletasks()
        for i, frame in enumerate(self.scroll_containers):
            # 親のキャンバスを取得して更新
            canvas = frame.master
            if isinstance(canvas, tk.Canvas):
                canvas.configure(scrollregion=canvas.bbox("all"))

        self.status_var.set("完了")

    def show_message(self, index, message, is_error=False):
        container = self.scroll_containers[index]
        self.clear_container(index)
        color = "red" if is_error else COLOR_TEXT_SUB
        tk.Label(container, text=message, bg=COLORS[index]["bg"], fg=color, font=FONT_M, pady=20).pack()
        self.status_var.set("更新終了")

if __name__ == "__main__":
    root = tk.Tk()
    app = KeywordNewsGadget(root)
    root.mainloop()
