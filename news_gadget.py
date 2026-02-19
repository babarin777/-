import tkinter as tk
from tkinter import ttk, font
import feedparser
import webbrowser
import requests
from PIL import Image, ImageTk
from io import BytesIO
import threading
import datetime
import time
import re

# --- Configuration ---
CATEGORIES = [
    {"name": "AI関連", "keyword": "AI", "bg": "AliceBlue"},
    {"name": "再エネ", "keyword": "再生可能エネルギー", "bg": "LavenderBlush"},
    {"name": "EV", "keyword": "EV 電気自動車", "bg": "Honeydew"}
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
FETCH_TIMEOUT = 15
MAX_THUMBNAILS_PER_SECTION = 3
VERIFY_SSL = True # Set to False if SSL certificates are broken in the environment

# --- UI Helpers ---
class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_window = tk.Frame(self.canvas)

        self.scrollable_window.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_window, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind mouse wheel only when entering the canvas
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_canvas_configure(self, event):
        # Resize the scrollable window to match the canvas width
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, 'delta'):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("News Gadget")
        self.root.geometry("500x800")

        self.setup_fonts()
        self.setup_ui()

        self.log("ガジェットを起動しました。")
        self.run_startup_diagnostics()

    def run_startup_diagnostics(self):
        def check():
            try:
                self.log("--- スタートアップ診断開始 ---")

                # 0. System Time
                now = datetime.datetime.now()
                self.log(f"・システム時刻: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                if now.year < 2024:
                    self.log("  警告: システム時刻が過去に設定されています。SSLエラーの原因になります。")

                # 1. Dependency Check
                try:
                    import feedparser, requests, PIL
                    from PIL import Image, ImageTk
                    self.log("・ライブラリ確認: OK (feedparser, requests, Pillow)")
                except ImportError as e:
                    self.log(f"・ライブラリ確認: NG ({e})")
                    self.log("  'pip install -r requirements.txt' を実行してください。")

                # 2. Internet Connectivity
                try:
                    res = requests.get("https://www.google.com", timeout=10, verify=VERIFY_SSL)
                    self.log(f"・インターネット接続: OK (status: {res.status_code})")
                except Exception as e:
                    self.log(f"・インターネット接続: NG ({e})")
                    if "SSL" in str(e) or "certificate" in str(e).lower():
                        self.log("  ヒント: SSL証明書エラーのようです。スクリプト内の VERIFY_SSL = False を試してください。")

                # 3. RSS Access
                try:
                    test_url = "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"
                    headers = {"User-Agent": USER_AGENT}
                    res = requests.get(test_url, headers=headers, timeout=10, verify=VERIFY_SSL)
                    self.log(f"・RSSアクセス: OK (status: {res.status_code}, length: {len(res.content)})")

                    if res.status_code == 200:
                        feed = feedparser.parse(res.content)
                        self.log(f"・解析テスト: {len(feed.entries)}件の記事を取得可能")
                    else:
                        self.log(f"  警告: ステータスコードが 200 ではありません。")
                except Exception as e:
                    self.log(f"・RSSアクセス: NG ({e})")

                self.log("--- 診断完了 ---")
                self.root.after(100, self.refresh_news)
            except Exception as e:
                print(f"Diagnostic Thread Crash: {e}")

        self.log("診断準備中...")
        threading.Thread(target=check, daemon=True).start()

    def setup_fonts(self):
        available_families = font.families()
        priority = ["Helvetica", "Arial", "Yu Gothic", "Meiryo"]
        self.base_font_family = "sans-serif"
        for f in priority:
            if f in available_families:
                self.base_font_family = f
                break

        self.title_font = font.Font(family=self.base_font_family, size=12, weight="bold")
        self.article_font = font.Font(family=self.base_font_family, size=10, weight="bold")
        self.meta_font = font.Font(family=self.base_font_family, size=8)
        self.log_font = font.Font(family=self.base_font_family, size=8)

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, pady=5, padx=10)
        header.pack(fill="x")

        tk.Label(header, text="最新ニュース", font=self.title_font).pack(side="left")

        self.stay_on_top_var = tk.BooleanVar(value=False)
        tk.Checkbutton(header, text="最前面表示", variable=self.stay_on_top_var, command=self.toggle_stay_on_top).pack(side="left", padx=10)

        tk.Button(header, text="更新", command=self.refresh_news).pack(side="right", padx=2)
        tk.Button(header, text="環境診断", command=self.run_startup_diagnostics).pack(side="right", padx=2)

        # Scrollable Area
        self.scroll_frame = ScrollableFrame(self.root)
        self.scroll_frame.pack(fill="both", expand=True)

        self.container = self.scroll_frame.scrollable_window

        # Log Area
        self.log_text = tk.Text(self.root, height=8, font=self.log_font, state="disabled", bg="#f0f0f0")
        self.log_text.pack(fill="x")

    def toggle_stay_on_top(self):
        self.root.attributes("-topmost", self.stay_on_top_var.get())

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        print(full_message) # Console output
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{full_message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def refresh_news(self):
        # Clear existing widgets
        for widget in self.container.winfo_children():
            widget.destroy()

        tk.Label(self.container, text="読み込み中...", font=self.article_font, pady=20).pack()

        self.log("ニュースを取得中...")
        threading.Thread(target=self.fetch_all_news, daemon=True).start()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def fetch_all_news(self):
        try:
            results = []
            for cat in CATEGORIES:
                self.log(f"{cat['name']} の情報を取得しています...")
                entries = self.get_news_entries(cat['keyword'])
                self.log(f"{cat['name']}: {len(entries)}件の記事が見つかりました。")
                sorted_entries = self.sort_entries(entries)
                results.append((cat, sorted_entries))

            # Update UI on main thread at once to clear "Loading..."
            self.root.after(0, self.render_all_categories, results)
            self.log("すべてのカテゴリの読み込みが完了しました。")
        except Exception as e:
            self.log(f"致命的なエラー: {e}")

    def render_all_categories(self, results):
        self.clear_container()
        if not results:
            tk.Label(self.container, text="データが取得できませんでした。", font=self.article_font, pady=20).pack()

        for cat, entries in results:
            self.render_category(cat, entries)

        # Final layout update
        self.container.update_idletasks()
        self.scroll_frame.canvas.configure(scrollregion=self.scroll_frame.canvas.bbox("all"))

    def get_news_entries(self, keyword):
        encoded_keyword = requests.utils.quote(keyword)
        rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"

        try:
            headers = {"User-Agent": USER_AGENT}
            try:
                response = requests.get(rss_url, headers=headers, timeout=FETCH_TIMEOUT, verify=VERIFY_SSL)
            except requests.exceptions.SSLError:
                self.log(f"SSL検証に失敗しました。検証なしで再試行します: {keyword}")
                response = requests.get(rss_url, headers=headers, timeout=FETCH_TIMEOUT, verify=False)

            if response.status_code != 200:
                self.log(f"エラー: {keyword} (HTTP {response.status_code}) 内容長: {len(response.content)}")
                if len(response.content) < 1000:
                    self.log(f"内容: {response.text}")
                return []

            feed = feedparser.parse(response.content)
            if feed.bozo:
                self.log(f"警告: {keyword} の解析例外: {feed.bozo_exception}")

            if not feed.entries:
                self.log(f"注意: {keyword} の記事が0件です。内容長: {len(response.content)}")
                if len(response.content) < 500:
                    self.log(f"レスポンス: {response.text}")

            return feed.entries
        except requests.exceptions.SSLError as e:
            self.log(f"SSLエラー: {keyword} の取得に失敗。証明書の問題かシステム時刻のズレの可能性があります。")
            self.log(f"詳細: {e}")
        except requests.exceptions.Timeout:
            self.log(f"エラー: {keyword} の取得がタイムアウトしました。")
        except requests.exceptions.ConnectionError:
            self.log(f"エラー: {keyword} 接続エラー。プロキシやファイアウォールを確認してください。")
        except Exception as e:
            self.log(f"エラー: {keyword} 予期せぬエラー ({type(e).__name__}): {e}")

        return []

    def sort_entries(self, entries):
        # Nikkei first, then latest
        def sort_key(entry):
            is_nikkei = 0
            if "日本経済新聞" in entry.get("source", {}).get("title", "") or "nikkei" in entry.link.lower():
                is_nikkei = 1

            published = entry.get("published_parsed")
            if published:
                dt = datetime.datetime(*published[:6])
            else:
                dt = datetime.datetime.min

            return (is_nikkei, dt)

        return sorted(entries, key=sort_key, reverse=True)

    def render_category(self, cat, entries):
        frame = tk.Frame(self.container, bg=cat['bg'], pady=10, padx=5)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text=cat['name'], font=self.title_font, bg=cat['bg'], fg="#333").pack(anchor="w", padx=5)

        if not entries:
            tk.Label(frame, text="記事が見つかりませんでした。接続やキーワードを確認してください。", font=self.article_font, bg=cat['bg']).pack(anchor="w", padx=10)
        else:
            for i, entry in enumerate(entries[:5]): # Show top 5
                self.render_article(frame, entry, cat['bg'], i < MAX_THUMBNAILS_PER_SECTION)

        # Force update scroll region
        self.root.after(100, lambda: self.scroll_frame.canvas.configure(scrollregion=self.scroll_frame.canvas.bbox("all")))

    def render_article(self, parent, entry, bg, fetch_image):
        card = tk.Frame(parent, bg="white", bd=1, relief="ridge", pady=5, padx=5)
        card.pack(fill="x", pady=2, padx=5)

        # Nikkei Badge
        source_name = entry.get("source", {}).get("title", "不明")
        is_nikkei = "日本経済新聞" in source_name or "nikkei" in entry.link.lower()

        if is_nikkei:
            badge = tk.Label(card, text="日経優先", bg="red", fg="white", font=self.meta_font, padx=2)
            badge.pack(anchor="w")

        title_label = tk.Label(card, text=entry.title, font=self.article_font, bg="white", wraplength=450, justify="left", cursor="hand2")
        title_label.pack(anchor="w")
        title_label.bind("<Button-1>", lambda e: webbrowser.open(entry.link))

        meta_text = f"{source_name} | {entry.get('published', '')}"
        tk.Label(card, text=meta_text, font=self.meta_font, bg="white", fg="gray").pack(anchor="w")

        if fetch_image:
            threading.Thread(target=self.load_thumbnail, args=(card, entry.link), daemon=True).start()

    def load_thumbnail(self, card, url):
        try:
            headers = {"User-Agent": USER_AGENT}
            res = requests.get(url, headers=headers, timeout=3)
            html = res.text
            # Simple regex to find og:image
            match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
            if not match:
                match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)

            if match:
                img_url = match.group(1)
                img_res = requests.get(img_url, headers=headers, timeout=3)
                img_data = Image.open(BytesIO(img_res.content))
                img_data.thumbnail((100, 100))

                # Process image to PhotoImage on the main thread
                self.root.after(0, self.process_and_display_image, card, img_data)
        except:
            pass # Silently fail for images

    def process_and_display_image(self, card, img_data):
        try:
            photo = ImageTk.PhotoImage(img_data)
            self.display_thumbnail(card, photo)
        except Exception as e:
            print(f"Image processing error: {e}")

    def display_thumbnail(self, card, photo):
        try:
            img_label = tk.Label(card, image=photo, bg="white")
            img_label.image = photo # Keep a reference
            img_label.pack(side="right", padx=5)
        except Exception as e:
            print(f"Display thumbnail error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsGadget(root)
    root.mainloop()
