import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import threading
import re
import html as html_lib
import urllib.parse
from io import BytesIO
import logging

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
    sys.exit(1)

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- デザイン設定 ---
COLORS = [
    {"bg": "#E1F5FE", "header": "#B3E5FC", "text": "#01579B"}, # Pale Blue
    {"bg": "#FCE4EC", "header": "#F8BBD0", "text": "#880E4F"}, # Pale Pink
    {"bg": "#E8F5E9", "header": "#C8E6C9", "text": "#1B5E20"}  # Pale Green
]
COLOR_CARD = "#FFFFFF"
COLOR_TEXT_SUB = "#607D8B"
COLOR_BORDER = "#CFD8DC"
COLOR_NIKKEI = "#FF9800" # 日経用アクセント

FONTS = ["Yu Gothic UI", "Meiryo", "MS PGothic", "Helvetica", "Arial", "sans-serif"]

def get_font(size, bold=False):
    weight = "bold" if bold else "normal"
    return (FONTS[0], size, weight)

class NewsCard(tk.Frame):
    def __init__(self, parent, title, link, date, source, card_bg=COLOR_CARD):
        super().__init__(parent, bg=card_bg, bd=1, relief=tk.FLAT, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.link = link
        self.card_bg = card_bg
        self.image_label = None

        # マウスイベントのバインド
        self.bind("<Button-1>", self.open_link)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

        # 内容の配置
        self.inner = tk.Frame(self, bg=card_bg, padx=12, pady=12)
        self.inner.pack(fill=tk.BOTH, expand=True)
        self.inner.bind("<Button-1>", self.open_link)

        # 日経フラグ
        is_nikkei = "日本経済新聞" in source or "日経" in title

        # ソースと日付
        meta_frame = tk.Frame(self.inner, bg=card_bg)
        meta_frame.pack(fill=tk.X)
        meta_frame.bind("<Button-1>", self.open_link)

        if is_nikkei:
            n_label = tk.Label(meta_frame, text="日経優先", fg="white", bg=COLOR_NIKKEI, font=get_font(8, True), padx=4)
            n_label.pack(side=tk.LEFT, padx=(0, 5))

        meta_text = f"{source} • {date}"
        tk.Label(meta_frame, text=meta_text, fg=COLOR_TEXT_SUB, bg=card_bg, font=get_font(9)).pack(side=tk.LEFT)

        # タイトル
        self.t_label = tk.Label(self.inner, text=title, fg="#263238", bg=card_bg, font=get_font(11, True),
                           wraplength=700, justify=tk.LEFT, cursor="hand2")
        self.t_label.pack(anchor=tk.W, pady=(5, 0))
        self.t_label.bind("<Button-1>", self.open_link)

    def set_image(self, photo):
        if self.image_label:
            self.image_label.destroy()

        self.image_label = tk.Label(self.inner, image=photo, bg=self.card_bg)
        self.image_label.image = photo # 参照保持
        self.image_label.pack(fill=tk.X, pady=(5, 5))
        self.image_label.bind("<Button-1>", self.open_link)
        # タイトルの前に持ってくる
        self.image_label.pack_forget()
        self.image_label.pack(fill=tk.X, pady=(0, 10), before=self.t_label)

    def open_link(self, event=None):
        webbrowser.open(self.link)

    def on_enter(self, event=None):
        self.update_bg("#F5F5F5")

    def on_leave(self, event=None):
        self.update_bg(self.card_bg)

    def update_bg(self, color):
        def _update(widget):
            # 日経タグ以外を更新
            if widget.winfo_class() == 'Label' and widget.cget("bg") == COLOR_NIKKEI:
                return
            widget.config(bg=color)
            for child in widget.winfo_children():
                _update(child)
        _update(self)

class KeywordNewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced News Gadget")
        self.root.geometry("900x950")
        self.root.configure(bg="#ECEFF1")

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        self.setup_ui()

    def setup_ui(self):
        # メインコンテナ
        main_container = tk.Frame(self.root, bg="#ECEFF1")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 入力エリア
        input_panel = tk.Frame(main_container, bg="#FFFFFF", padx=15, pady=15, bd=0)
        input_panel.pack(fill=tk.X)

        tk.Label(input_panel, text="Keyword News Gadget", font=get_font(18, True), bg="#FFFFFF", fg="#37474F").pack(pady=(0, 10))

        entry_frame = tk.Frame(input_panel, bg="#FFFFFF")
        entry_frame.pack(fill=tk.X)

        self.entries = []
        default_kw = ["人工知能", "電気自動車", "半導体"]
        for i in range(3):
            f = tk.Frame(entry_frame, bg="#FFFFFF")
            f.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
            tk.Label(f, text=f"キーワード {i+1}", font=get_font(9), bg="#FFFFFF", fg=COLOR_TEXT_SUB).pack(anchor=tk.W)
            e = tk.Entry(f, font=get_font(11), bd=1, relief=tk.SOLID)
            e.pack(fill=tk.X, pady=2)
            e.insert(0, default_kw[i])
            self.entries.append(e)

        btn_frame = tk.Frame(input_panel, bg="#FFFFFF")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.search_btn = tk.Button(btn_frame, text="🔄 全て更新", command=self.refresh_all,
                                   bg="#455A64", fg="white", font=get_font(11, True), relief=tk.FLAT, padx=30, pady=8, cursor="hand2")
        self.search_btn.pack(side=tk.LEFT)

        self.ontop_var = tk.BooleanVar(value=False)
        self.ontop_check = tk.Checkbutton(btn_frame, text="最前面表示", variable=self.ontop_var,
                                          command=self.toggle_ontop, bg="#FFFFFF", font=get_font(9))
        self.ontop_check.pack(side=tk.LEFT, padx=20)

        self.status_label = tk.Label(btn_frame, text="Ready", font=get_font(9), bg="#FFFFFF", fg=COLOR_TEXT_SUB)
        self.status_label.pack(side=tk.RIGHT, pady=5)

        # スクロールエリア
        outer_scroll = tk.Frame(main_container, bg="#ECEFF1")
        outer_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(outer_scroll, bg="#ECEFF1", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_scroll, orient="vertical", command=self.canvas.yview)
        self.scroll_content = tk.Frame(self.canvas, bg="#ECEFF1")

        self.scroll_content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw", width=860)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # マウスホイール
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # 各セクション
        self.sections = []
        for i in range(3):
            sec_frame = tk.Frame(self.scroll_content, bg=COLORS[i]["bg"], padx=10, pady=10)
            sec_frame.pack(fill=tk.X, pady=5)

            header = tk.Frame(sec_frame, bg=COLORS[i]["header"], padx=10, pady=5)
            header.pack(fill=tk.X)

            title_label = tk.Label(header, text=f"Keyword {i+1}", font=get_font(12, True),
                                  bg=COLORS[i]["header"], fg=COLORS[i]["text"])
            title_label.pack(side=tk.LEFT)

            content_area = tk.Frame(sec_frame, bg=COLORS[i]["bg"])
            content_area.pack(fill=tk.X, pady=5)

            self.sections.append({"frame": sec_frame, "title": title_label, "content": content_area})

        # ログエリア
        self.log_text = tk.Text(main_container, height=4, bg="#263238", fg="#CFD8DC", font=("Consolas", 8))
        self.log_text.pack(fill=tk.X)
        self.log_text.insert(tk.END, "Application started.\n")

    def toggle_ontop(self):
        self.root.attributes("-topmost", self.ontop_var.get())

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        logging.info(message)

    def refresh_all(self):
        keywords = [e.get().strip() for e in self.entries]
        if not any(keywords):
            messagebox.showwarning("Warning", "Please enter at least one keyword.")
            return

        self.status_label.config(text="Updating...")
        for i, kw in enumerate(keywords):
            if kw:
                self.sections[i]["title"].config(text=f"🔍 {kw}")
                threading.Thread(target=self.fetch_keyword, args=(i, kw), daemon=True).start()
            else:
                self.sections[i]["title"].config(text="(Empty)")
                self.clear_section(i)

    def clear_section(self, index):
        for widget in self.sections[index]["content"].winfo_children():
            widget.destroy()

    def fetch_keyword(self, index, keyword):
        self.root.after(0, lambda: self.clear_section(index))
        self.root.after(0, lambda: tk.Label(self.sections[index]["content"], text="Loading...",
                                           bg=COLORS[index]["bg"], font=get_font(10)).pack(pady=10))

        encoded_query = urllib.parse.quote(keyword)
        # キーワードに合致するものを検索（日経優先は後のソートで行う）
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            self.log(f"Fetching RSS for '{keyword}'...")
            response = requests.get(url, headers=self.headers, timeout=15)
            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.log(f"No results for '{keyword}'.")
                self.root.after(0, lambda: self.show_empty(index))
                return

            sorted_entries = sorted(feed.entries, key=lambda e: (
                ("日本経済新聞" in (e.source.title if hasattr(e, 'source') else "") or "日経" in e.title),
                getattr(e, 'published_parsed', 0)
            ), reverse=True)

            entries_to_show = sorted_entries[:10]
            self.root.after(0, lambda: self.display_entries(index, entries_to_show))

        except Exception as e:
            self.log(f"Error fetching '{keyword}': {str(e)}")
            self.root.after(0, lambda: self.show_error(index, str(e)))

    def display_entries(self, index, entries):
        self.clear_section(index)
        content_area = self.sections[index]["content"]

        cards = []
        for entry in entries:
            title = entry.title
            link = entry.link
            date = getattr(entry, 'published', "")
            source = entry.source.title if hasattr(entry, 'source') else "News"

            card = NewsCard(content_area, title, link, date, source, card_bg=COLOR_CARD)
            card.pack(fill=tk.X, pady=5)
            cards.append((card, link))

        self.status_label.config(text="Done")

        for card, link in cards[:5]:
            threading.Thread(target=self.fetch_and_update_image, args=(card, link), daemon=True).start()

    def fetch_and_update_image(self, card, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=5)
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

                img_res = requests.get(img_url, headers=self.headers, timeout=5)
                img = Image.open(BytesIO(img_res.content))
                img.thumbnail((700, 350))
                self.root.after(0, lambda: self.apply_image(card, img))
        except:
            pass

    def apply_image(self, card, img):
        try:
            photo = ImageTk.PhotoImage(img)
            card.set_image(photo)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except:
            pass

    def show_empty(self, index):
        self.clear_section(index)
        tk.Label(self.sections[index]["content"], text="記事が見つかりませんでした。",
                 bg=COLORS[index]["bg"], fg=COLOR_TEXT_SUB, font=get_font(10)).pack(pady=20)

    def show_error(self, index, msg):
        self.clear_section(index)
        tk.Label(self.sections[index]["content"], text=f"Error: {msg}",
                 bg=COLORS[index]["bg"], fg="red", font=get_font(10)).pack(pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = KeywordNewsGadget(root)
    root.mainloop()
