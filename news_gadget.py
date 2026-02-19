import tkinter as tk
from tkinter import ttk
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import webbrowser
import threading
import re
import html as html_lib
import ssl
from io import BytesIO
from PIL import Image, ImageTk

# --- デザイン設定 ---
COLOR_BG = "#f9fbf7"        # さらに淡いグリーン
COLOR_HEADER = "#e8f5e9"    # ヘッダー用グリーン
COLOR_CARD = "#ffffff"      # 白
COLOR_TEXT_MAIN = "#1b5e20" # 濃いグリーン
COLOR_TEXT_SUB = "#4e7d52"  # 中間のグリーン
COLOR_ACCENT = "#66bb6a"    # アクセント
COLOR_BORDER = "#dcedc8"    # 境界線

# フォント設定（マルチプラットフォーム対応）
FONT_FAMILY = ("Yu Gothic UI", "Meiryo", "Hiragino Kaku Gothic ProN", "Helvetica", "Arial", "sans-serif")

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Visual News & Video Trends")
        self.root.geometry("1000x850")
        self.root.configure(bg=COLOR_BG)

        # カテゴリ定義（映像系を追加）
        self.categories = [
            {"id": "ai", "name": "AI 🤖", "query": "AI OR 人工知能"},
            {"id": "re", "name": "再エネ 🌱", "query": "再生可能エネルギー OR 再エネ"},
            {"id": "ev", "name": "EV 🚗", "query": "EV OR 電気自動車"},
            {"id": "video", "name": "映像・動画 🎬", "query": "(AI OR 再エネ OR EV) (動画 OR 映像 OR YouTube)"}
        ]

        self.images = {} # 画像参照保持
        self.setup_styles()
        self.setup_ui()
        self.log("Application started.")

    def log(self, message):
        """デバッグ用のログ出力"""
        print(f"[LOG] {message}")
        if hasattr(self, 'debug_text'):
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"{message}\n")
            self.debug_text.see(tk.END)
            self.debug_text.config(state=tk.DISABLED)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=COLOR_BORDER,
                        foreground=COLOR_TEXT_MAIN,
                        padding=[20, 10],
                        font=(FONT_FAMILY[0], 11, 'bold'))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD)],
                  foreground=[("selected", COLOR_TEXT_MAIN)])

        style.configure("Update.TButton",
                        background=COLOR_ACCENT,
                        foreground="white",
                        font=(FONT_FAMILY[0], 10, 'bold'),
                        borderwidth=0)

    def setup_ui(self):
        # メインコンテナ
        self.main_container = tk.Frame(self.root, bg=COLOR_BG, padx=20, pady=10)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ヘッダー
        header = tk.Frame(self.main_container, bg=COLOR_HEADER, padx=20, pady=15,
                          highlightbackground=COLOR_BORDER, highlightthickness=1)
        header.pack(fill=tk.X, pady=(0, 15))

        title_label = tk.Label(header, text="TECH & VISUAL TRENDS",
                               bg=COLOR_HEADER, fg=COLOR_TEXT_MAIN,
                               font=('Impact', 26) if 'Impact' in self.root.tk.call('font', 'families') else (FONT_FAMILY[0], 24, 'bold'))
        title_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(header, text="Ready", bg=COLOR_HEADER,
                                     fg=COLOR_TEXT_SUB, font=(FONT_FAMILY[0], 9))
        self.status_label.pack(side=tk.LEFT, padx=20, pady=10)

        refresh_btn = ttk.Button(header, text="🔄 最新に更新",
                                 command=self.refresh_all,
                                 style="Update.TButton")
        refresh_btn.pack(side=tk.RIGHT)

        # タブ
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_widgets = {}

        for cat in self.categories:
            cat_id = cat["id"]
            frame = tk.Frame(self.notebook, bg=COLOR_CARD)
            self.notebook.add(frame, text=cat["name"])

            txt = tk.Text(frame,
                          bg=COLOR_CARD,
                          fg="#333333",
                          padx=25, pady=25,
                          font=(FONT_FAMILY[0], 11),
                          wrap=tk.WORD,
                          borderwidth=0,
                          cursor="arrow",
                          state=tk.DISABLED)

            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=txt.yview)
            txt.configure(yscrollcommand=scrollbar.set)

            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # タグ設定
            txt.tag_configure("featured_title", font=(FONT_FAMILY[0], 18, 'bold'), foreground=COLOR_TEXT_MAIN, spacing1=10, spacing3=10)
            txt.tag_configure("title", font=(FONT_FAMILY[0], 12, 'bold'), spacing1=15)
            txt.tag_configure("date", foreground="#888888", font=(FONT_FAMILY[0], 9))
            txt.tag_configure("sep", foreground=COLOR_BORDER)
            txt.tag_configure("video_tag", background="#ffebee", foreground="#c62828", font=(FONT_FAMILY[0], 9, 'bold'))

            self.text_widgets[cat_id] = txt

        # ログタブ（デバッグ用）
        debug_frame = tk.Frame(self.notebook, bg="#f5f5f5")
        self.notebook.add(debug_frame, text="Log 📋")
        self.debug_text = tk.Text(debug_frame, bg="#f5f5f5", fg="#666666", font=("Courier", 9), state=tk.DISABLED)
        self.debug_text.pack(fill=tk.BOTH, expand=True)

        # 注意事項ラベル
        note_label = tk.Label(self.main_container, text="※動画はブラウザで再生されます。直接再生には対応していません。",
                              bg=COLOR_BG, fg=COLOR_TEXT_SUB, font=(FONT_FAMILY[0], 8))
        note_label.pack(anchor=tk.W, pady=5)

        self.refresh_all()

    def refresh_all(self):
        self.log("Refreshing all feeds...")
        self.status_label.config(text="更新中...")
        for cat in self.categories:
            cat_id = cat["id"]
            txt = self.text_widgets[cat_id]
            txt.config(state=tk.NORMAL)
            txt.delete('1.0', tk.END)
            txt.insert(tk.END, f"\n   最新の {cat['name']} 情報を取得しています...\n", "date")
            txt.config(state=tk.DISABLED)
            threading.Thread(target=self.fetch_news, args=(cat,), daemon=True).start()

    def fetch_news(self, cat):
        cat_id = cat["id"]
        cat_name = cat["name"]
        query = cat["query"]
        self.log(f"Starting fetch for {cat_name}")

        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            # SSL証明書エラー対策（必要に応じて）
            context = ssl._create_unverified_context()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            with urllib.request.urlopen(req, timeout=20, context=context) as response:
                content = response.read()

            self.log(f"Received data for {cat_name} ({len(content)} bytes)")
            root = ET.fromstring(content)
            items = root.findall('./channel/item')
            self.log(f"Parsed {len(items)} items for {cat_name}")

            featured_image = None
            if items:
                top_link = items[0].find('link').text
                featured_image = self.get_og_image(top_link)

            self.root.after(0, self.update_display, cat_id, items, featured_image)

        except Exception as e:
            self.log(f"Error in fetch_news for {cat_name}: {e}")
            self.root.after(0, lambda: self.show_error(cat_id, str(e)))

    def get_og_image(self, url):
        self.log(f"Attempting to fetch image for: {url[:50]}...")
        try:
            context = ssl._create_unverified_context()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                html = response.read().decode('utf-8', errors='ignore')

            match = re.search(r'<meta [^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html)

            if match:
                img_url = html_lib.unescape(match.group(1))
                if img_url.startswith('//'): img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed = urllib.parse.urlparse(url)
                    img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"

                self.log(f"Found image URL: {img_url[:50]}")
                with urllib.request.urlopen(img_url, timeout=10, context=context) as img_res:
                    img_data = img_res.read()

                if not img_data:
                    return None

                img = Image.open(BytesIO(img_data))
                img.thumbnail((700, 350))
                return img
        except Exception as e:
            self.log(f"Image fetch skipped: {e}")
        return None

    def update_display(self, cat_id, items, featured_img_obj):
        self.log(f"Updating display for {cat_id}")
        txt = self.text_widgets[cat_id]
        txt.config(state=tk.NORMAL)
        txt.delete('1.0', tk.END)

        if not items:
            txt.insert(tk.END, "\n   ニュースが見つかりませんでした。", "date")
            txt.config(state=tk.DISABLED)
            return

        # 画像表示
        if featured_img_obj:
            try:
                photo = ImageTk.PhotoImage(featured_img_obj)
                self.images[f"{cat_id}_top"] = photo
                txt.image_create(tk.END, image=photo)
                txt.insert(tk.END, "\n")
            except Exception as e:
                self.log(f"UI Error displaying image: {e}")

        for i, item in enumerate(items):
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""

            tag_name = f"link_{cat_id}_{i}"

            # 映像・動画が含まれるかチェック
            is_video = any(kw in title for kw in ["動画", "映像", "YouTube", "配信", "ムービー"])

            if i == 0:
                txt.insert(tk.END, f"🌟 FEATURED STORY ", "date")
                if is_video: txt.insert(tk.END, " [VIDEO] ", "video_tag")
                txt.insert(tk.END, "\n")
                txt.insert(tk.END, title + "\n", ("featured_title", tag_name))
            else:
                txt.insert(tk.END, f"🗓 {pub_date} ", "date")
                if is_video: txt.insert(tk.END, " [VIDEO] ", "video_tag")
                txt.insert(tk.END, "\n")
                txt.insert(tk.END, title + "\n", ("title", tag_name))

            if link:
                txt.tag_bind(tag_name, "<Button-1>", lambda e, l=link: webbrowser.open(l))
                txt.tag_bind(tag_name, "<Enter>", lambda e: txt.config(cursor="hand2"))
                txt.tag_bind(tag_name, "<Leave>", lambda e: txt.config(cursor="arrow"))
                txt.tag_configure(tag_name, foreground="#2e7d32", underline=True)

            txt.insert(tk.END, "\n" + "─" * 70 + "\n\n", "sep")

        txt.config(state=tk.DISABLED)
        self.status_label.config(text="Update Complete")
        self.log(f"Update finished for {cat_id}")

    def show_error(self, cat_id, error_msg):
        txt = self.text_widgets[cat_id]
        txt.config(state=tk.NORMAL)
        txt.delete('1.0', tk.END)
        txt.insert(tk.END, f"\n   エラーが発生しました。\n\n   詳細: {error_msg}\n\n   インターネット接続やセキュリティ設定を確認してください。", "date")
        txt.config(state=tk.DISABLED)
        self.status_label.config(text="Update Failed")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsGadget(root)
    root.mainloop()
