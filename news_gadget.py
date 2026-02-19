import tkinter as tk
from tkinter import ttk
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import webbrowser
import threading
import re
import html as html_lib
import sys
from io import BytesIO
from PIL import Image, ImageTk

# カラーパレット（清潔感のあるパステルグリーン）
COLOR_BG = "#f1f8e9"      # 非常に淡いグリーン
COLOR_CARD = "#ffffff"    # 白
COLOR_TEXT_MAIN = "#2e7d32" # 濃いグリーン
COLOR_TEXT_SUB = "#616161"  # グレー
COLOR_ACCENT = "#81c784"    # 中間のグリーン
COLOR_BORDER = "#c5e1a5"    # 境界線

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Tech Trends - Visual News Gadget")
        self.root.geometry("900x800")
        self.root.configure(bg=COLOR_BG)

        # 内部処理用のIDを付与
        self.categories = [
            {"id": "ai", "name": "AI 🤖", "query": "AI OR 人工知能"},
            {"id": "re", "name": "再エネ 🌱", "query": "再生可能エネルギー OR 再エネ"},
            {"id": "ev", "name": "EV 🚗", "query": "EV OR 電気自動車"}
        ]

        self.images = {} # 画像参照保持用
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=COLOR_BORDER,
                        foreground=COLOR_TEXT_MAIN,
                        padding=[20, 8],
                        font=('Yu Gothic', 11, 'bold'))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD)],
                  foreground=[("selected", COLOR_TEXT_MAIN)])

        style.configure("Update.TButton",
                        background=COLOR_ACCENT,
                        foreground="white",
                        font=('Yu Gothic', 10, 'bold'),
                        borderwidth=0)

    def setup_ui(self):
        # メインコンテナ
        self.main_container = tk.Frame(self.root, bg=COLOR_BG, padx=30, pady=20)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ヘッダー
        header = tk.Frame(self.main_container, bg=COLOR_BG)
        header.pack(fill=tk.X, pady=(0, 20))

        title_label = tk.Label(header, text="TECH TRENDS EXPLORER",
                               bg=COLOR_BG, fg=COLOR_TEXT_MAIN,
                               font=('Impact', 28))
        title_label.pack(side=tk.LEFT)

        self.status_label = tk.Label(header, text="", bg=COLOR_BG, fg=COLOR_TEXT_SUB, font=('Yu Gothic', 9))
        self.status_label.pack(side=tk.LEFT, padx=20, pady=15)

        refresh_btn = ttk.Button(header, text="🔄 フィードを更新",
                                 command=self.refresh_all,
                                 style="Update.TButton")
        refresh_btn.pack(side=tk.RIGHT, pady=5)

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
                          fg=COLOR_TEXT_MAIN,
                          padx=30, pady=30,
                          font=('Yu Gothic', 11),
                          wrap=tk.WORD,
                          borderwidth=0,
                          cursor="arrow",
                          state=tk.DISABLED)

            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=txt.yview)
            txt.configure(yscrollcommand=scrollbar.set)

            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # タグ設定
            txt.tag_configure("featured_title", font=('Yu Gothic', 18, 'bold'), spacing1=10, spacing3=10)
            txt.tag_configure("title", font=('Yu Gothic', 12, 'bold'), spacing1=15)
            txt.tag_configure("date", foreground=COLOR_TEXT_SUB, font=('Yu Gothic', 9))
            txt.tag_configure("sep", foreground=COLOR_BORDER)

            self.text_widgets[cat_id] = txt

        self.refresh_all()

    def refresh_all(self):
        print("Refreshing all feeds...")
        self.status_label.config(text="更新中...")
        for cat in self.categories:
            cat_id = cat["id"]
            txt = self.text_widgets[cat_id]
            txt.config(state=tk.NORMAL)
            txt.delete('1.0', tk.END)
            txt.insert(tk.END, f"\n   最新の {cat['name']} 情報を取得中...\n", "date")
            txt.config(state=tk.DISABLED)
            threading.Thread(target=self.fetch_news, args=(cat,), daemon=True).start()

    def fetch_news(self, cat):
        cat_id = cat["id"]
        cat_name = cat["name"]
        query = cat["query"]
        print(f"Fetching news for: {cat_name}")

        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()

            root = ET.fromstring(content)
            items = root.findall('./channel/item')
            print(f"Found {len(items)} items for {cat_name}")

            featured_image = None
            if items:
                top_link = items[0].find('link').text
                featured_image = self.get_og_image(top_link)

            self.root.after(0, self.update_display, cat_id, items, featured_image)

        except Exception as e:
            print(f"Error fetching {cat_name}: {e}")
            self.root.after(0, lambda: self.show_error(cat_id, str(e)))

    def get_og_image(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=7) as response:
                html = response.read().decode('utf-8', errors='ignore')

            match = re.search(r'<meta [^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
            if not match:
                match = re.search(r'<meta [^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html)

            if match:
                img_url = html_lib.unescape(match.group(1))
                # 相対パスの解決
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed_url = urllib.parse.urlparse(url)
                    img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{img_url}"
                elif not img_url.startswith('http'):
                    parsed_url = urllib.parse.urlparse(url)
                    base_path = parsed_url.path.rsplit('/', 1)[0]
                    img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}/{img_url}"

                print(f"Found image: {img_url[:60]}...")
                with urllib.request.urlopen(img_url, timeout=7) as img_res:
                    img_data = img_res.read()

                img = Image.open(BytesIO(img_data))
                img.thumbnail((600, 300))
                return img
        except Exception as e:
            print(f"Image fetch skipped: {e}")
        return None

    def update_display(self, cat_id, items, featured_img_obj):
        txt = self.text_widgets[cat_id]
        txt.config(state=tk.NORMAL)
        txt.delete('1.0', tk.END)

        if not items:
            txt.insert(tk.END, "\n   ニュースが見つかりませんでした。", "date")
            txt.config(state=tk.DISABLED)
            return

        # 画像の処理と表示（メインスレッドで実行）
        if featured_img_obj:
            try:
                photo = ImageTk.PhotoImage(featured_img_obj)
                self.images[f"{cat_id}_top"] = photo
                txt.image_create(tk.END, image=photo)
                txt.insert(tk.END, "\n")
            except Exception as e:
                print(f"Error displaying image: {e}")

        for i, item in enumerate(items):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')

            title = title_elem.text if title_elem is not None else "No Title"
            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""

            # タグ名に絵文字を含めない
            tag_name = f"link_{cat_id}_{i}"

            if i == 0:
                txt.insert(tk.END, f"🌟 FEATURED STORY\n", "date")
                txt.insert(tk.END, title + "\n", ("featured_title", tag_name))
            else:
                txt.insert(tk.END, f"🗓 {pub_date}\n", "date")
                txt.insert(tk.END, title + "\n", ("title", tag_name))

            if link:
                txt.tag_bind(tag_name, "<Button-1>", lambda e, l=link: webbrowser.open(l))
                txt.tag_bind(tag_name, "<Enter>", lambda e: txt.config(cursor="hand2"))
                txt.tag_bind(tag_name, "<Leave>", lambda e: txt.config(cursor="arrow"))
                txt.tag_configure(tag_name, foreground="#1b5e20", underline=True)

            txt.insert(tk.END, "\n" + "─" * 60 + "\n\n", "sep")

        txt.config(state=tk.DISABLED)
        self.status_label.config(text="更新完了")
        print(f"Display updated for {cat_id}")

    def show_error(self, cat_id, error_msg):
        txt = self.text_widgets[cat_id]
        txt.config(state=tk.NORMAL)
        txt.delete('1.0', tk.END)
        txt.insert(tk.END, f"\n   エラーが発生しました:\n   {error_msg}\n\n   ネットワーク接続を確認してください。", "date")
        txt.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsGadget(root)
    root.mainloop()
