import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import webbrowser
import threading

# カラースキーム
COLOR_BG = "#1e1e2e"        # ダーク背景
COLOR_CARD = "#2a2a3d"      # カード背景
COLOR_TEXT = "#cdd6f4"      # メインテキスト
COLOR_DATE = "#a6adc8"      # 日付テキスト
COLOR_LINK = "#89b4fa"      # リンク色
COLOR_ACCENT = "#fab387"    # アクセント（更新ボタン等）
COLOR_TAB_BG = "#181825"
COLOR_SEPARATOR = "#45475a"

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Modern Tech News Gadget")
        self.root.geometry("700x650")
        self.root.configure(bg=COLOR_BG)

        self.categories = {
            "AI 🤖": "AI OR 人工知能",
            "再エネ 🌱": "再生可能エネルギー OR 再エネ",
            "EV 🚗": "EV OR 電気自動車"
        }

        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('default')

        # タブのスタイル
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=COLOR_TAB_BG,
                        foreground=COLOR_TEXT,
                        padding=[15, 5],
                        font=('Helvetica', 10, 'bold'))
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_CARD)],
                  foreground=[("selected", COLOR_ACCENT)])

        # ボタンのスタイル
        style.configure("Accent.TButton",
                        background=COLOR_ACCENT,
                        foreground=COLOR_BG,
                        font=('Helvetica', 10, 'bold'))

    def setup_ui(self):
        # メインフレーム
        main_frame = tk.Frame(self.root, bg=COLOR_BG, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトルラベル
        title_label = tk.Label(main_frame, text="LATEST TECH TRENDS",
                               bg=COLOR_BG, fg=COLOR_ACCENT,
                               font=('Helvetica', 18, 'bold'))
        title_label.pack(pady=(0, 20))

        # タブコントロール
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_widgets = {}

        for cat in self.categories:
            frame = tk.Frame(self.notebook, bg=COLOR_CARD)
            self.notebook.add(frame, text=cat)

            # テキストエリア
            txt = tk.Text(frame,
                          bg=COLOR_CARD,
                          fg=COLOR_TEXT,
                          insertbackground=COLOR_TEXT,
                          padx=20, pady=20,
                          font=('Helvetica', 11),
                          wrap=tk.WORD,
                          borderwidth=0,
                          cursor="arrow")

            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=txt.yview)
            txt.configure(yscrollcommand=scrollbar.set)

            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # タグ設定
            txt.tag_configure("title", font=('Helvetica', 12, 'bold'), spacing1=10)
            txt.tag_configure("date", foreground=COLOR_DATE, font=('Helvetica', 9))
            txt.tag_configure("link", foreground=COLOR_LINK, underline=True)
            txt.tag_configure("separator", foreground=COLOR_SEPARATOR)

            self.text_widgets[cat] = txt

        # 更新ボタン
        btn_frame = tk.Frame(main_frame, bg=COLOR_BG)
        btn_frame.pack(fill=tk.X, pady=(20, 0))

        refresh_btn = ttk.Button(btn_frame, text="UPDATE FEED",
                                 command=self.refresh_all,
                                 style="Accent.TButton")
        refresh_btn.pack(side=tk.RIGHT)

        # 初回読み込み
        self.refresh_all()

    def refresh_all(self):
        for cat in self.categories:
            txt = self.text_widgets[cat]
            txt.config(state=tk.NORMAL)
            txt.delete('1.0', tk.END)
            txt.insert(tk.END, f"\n   Fetching latest {cat} news...\n", "date")
            txt.config(state=tk.DISABLED)
            threading.Thread(target=self.fetch_news, args=(cat,), daemon=True).start()

    def fetch_news(self, category):
        query = self.categories[category]
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                content = response.read()

            root = ET.fromstring(content)
            items = root.findall('./channel/item')

            self.root.after(0, self.update_display, category, items)

        except Exception as e:
            self.root.after(0, lambda: self.show_error(category, str(e)))

    def update_display(self, category, items):
        txt = self.text_widgets[category]
        txt.config(state=tk.NORMAL)
        txt.delete('1.0', tk.END)

        if not items:
            txt.insert(tk.END, "\n   No news found.", "date")
            txt.config(state=tk.DISABLED)
            return

        for i, item in enumerate(items):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')

            title = title_elem.text if title_elem is not None else "No Title"
            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""

            # 日付
            if pub_date:
                txt.insert(tk.END, f"🗓 {pub_date}\n", "date")

            # タイトル
            tag_name = f"link_{i}"
            txt.insert(tk.END, title + "\n", ("title", tag_name))

            # リンクイベント
            if link:
                txt.tag_bind(tag_name, "<Button-1>", lambda e, l=link: webbrowser.open(l))
                txt.tag_bind(tag_name, "<Enter>", lambda e: txt.config(cursor="hand2"))
                txt.tag_bind(tag_name, "<Leave>", lambda e: txt.config(cursor="arrow"))

            # セパレーター
            txt.insert(tk.END, "─" * 40 + "\n\n", "separator")

        txt.config(state=tk.DISABLED)

    def show_error(self, category, error_msg):
        txt = self.text_widgets[category]
        txt.config(state=tk.NORMAL)
        txt.delete('1.0', tk.END)
        txt.insert(tk.END, f"\n   Error: {error_msg}", "date")
        txt.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsGadget(root)
    root.mainloop()
