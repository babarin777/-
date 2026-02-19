import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import webbrowser
import threading

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("最新情報ガジェット (AI, 再エネ, EV)")
        self.root.geometry("600x500")

        self.categories = {
            "AI": "AI OR 人工知能",
            "再エネ": "再生可能エネルギー OR 再エネ",
            "EV": "EV OR 電気自動車"
        }

        self.setup_ui()

    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タブコントロール
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_widgets = {}

        for cat in self.categories:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=cat)

            # テキストエリアとスクロールバー
            txt = tk.Text(frame, wrap=tk.WORD, cursor="arrow")
            scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=txt.yview)
            txt.configure(yscrollcommand=scrollbar.set)

            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # リンク用のタグ設定
            txt.tag_configure("link", foreground="blue", underline=True)
            txt.tag_bind("link", "<Enter>", lambda e: txt.config(cursor="hand2"))
            txt.tag_bind("link", "<Leave>", lambda e: txt.config(cursor="arrow"))

            self.text_widgets[cat] = txt

        # 更新ボタン
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        refresh_btn = ttk.Button(btn_frame, text="最新情報に更新", command=self.refresh_all)
        refresh_btn.pack(side=tk.RIGHT)

        # 初回読み込み
        self.refresh_all()

    def refresh_all(self):
        for cat in self.categories:
            self.text_widgets[cat].delete('1.0', tk.END)
            self.text_widgets[cat].insert(tk.END, f"{cat} のニュースを読み込み中...\n")
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

            # UI更新はメインスレッドで行う
            self.root.after(0, self.update_display, category, items)

        except Exception as e:
            self.root.after(0, lambda: self.show_error(category, str(e)))

    def update_display(self, category, items):
        txt = self.text_widgets[category]
        txt.delete('1.0', tk.END)

        if not items:
            txt.insert(tk.END, "ニュースが見つかりませんでした。")
            return

        for i, item in enumerate(items):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')

            title = title_elem.text if title_elem is not None else "No Title"
            link = link_elem.text if link_elem is not None else ""
            pub_date = pub_date_elem.text if pub_date_elem is not None else ""

            # 日付を表示
            if pub_date:
                txt.insert(tk.END, f"【{pub_date}】\n")

            # タイトルを挿入
            tag_name = f"link_{i}"
            txt.insert(tk.END, title + "\n", tag_name)

            # リンクがあればクリックイベントをバインド
            if link:
                txt.tag_bind(tag_name, "<Button-1>", lambda e, l=link: webbrowser.open(l))
                txt.tag_configure(tag_name, foreground="blue", underline=True)
                txt.tag_bind(tag_name, "<Enter>", lambda e: txt.config(cursor="hand2"))
                txt.tag_bind(tag_name, "<Leave>", lambda e: txt.config(cursor="arrow"))

            txt.insert(tk.END, "\n" + "-"*50 + "\n\n")

    def show_error(self, category, error_msg):
        txt = self.text_widgets[category]
        txt.delete('1.0', tk.END)
        txt.insert(tk.END, f"エラーが発生しました: {error_msg}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsGadget(root)
    root.mainloop()
