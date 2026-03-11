import tkinter as tk
from tkinter import ttk
import webbrowser
import feedparser
import requests
from PIL import Image, ImageTk
import io
import threading
from datetime import datetime
import re
from urllib.parse import quote

class NewsGadget:
    def __init__(self, root):
        self.root = root
        self.root.title("Latest Tech & Energy News")
        self.root.geometry("700x900")

        # Stay on Top state
        self.stay_on_top = tk.BooleanVar(value=False)

        # Configure fonts
        # Choose the first available font
        self.base_font = self._get_best_font()
        self.title_font = (self.base_font, 11, "bold")
        self.source_font = (self.base_font, 9)
        self.date_font = (self.base_font, 8)
        self.header_font = (self.base_font, 16, "bold")

        # Keywords and Colors
        self.categories = [
            {"keyword": "AI関連", "bg_color": "#f0f8ff", "display_name": "AI関連"},      # AliceBlue
            {"keyword": "再エネ", "bg_color": "#fff0f5", "display_name": "再生可能エネルギー"}, # LavenderBlush
            {"keyword": "EV", "bg_color": "#f0fff0", "display_name": "EV (電気自動車)"}    # Honeydew
        ]

        self.setup_ui()
        self.fetch_all_news()

    def setup_ui(self):
        # Top Control Bar
        self.control_bar = tk.Frame(self.root, bg="#333", pady=5)
        self.control_bar.pack(side="top", fill="x")

        self.refresh_btn = tk.Button(
            self.control_bar, text="更新", command=self.fetch_all_news,
            bg="#555", fg="white", activebackground="#777", activeforeground="white",
            relief="flat", padx=10
        )
        self.refresh_btn.pack(side="left", padx=10)

        self.top_toggle = tk.Checkbutton(
            self.control_bar, text="最前面表示", variable=self.stay_on_top,
            command=self.toggle_stay_on_top, bg="#333", fg="white",
            selectcolor="#555", activebackground="#444", activeforeground="white"
        )
        self.top_toggle.pack(side="right", padx=10)

        # Create Main Canvas and Scrollbar
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg="#f5f5f5")
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f5f5f5")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Log Area
        self.log_frame = tk.Frame(self.root, bg="#eee", height=20)
        self.log_frame.pack(side="bottom", fill="x")
        self.log_label = tk.Label(self.log_frame, text="Ready", font=(self.base_font, 7), bg="#eee", fg="#666")
        self.log_label.pack(side="left", padx=5)

        # Mouse wheel binding - localized to activate on Enter and deactivate on Leave
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
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _get_best_font(self):
        from tkinter import font
        available = font.families()
        for f in ("Yu Gothic", "Meiryo", "Hiragino Kaku Gothic ProN", "MS PGothic", "Helvetica", "Arial"):
            if f in available:
                return f
        return "sans-serif"

    def toggle_stay_on_top(self):
        self.root.attributes("-topmost", self.stay_on_top.get())

    def fetch_all_news(self):
        # Clear existing content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.log("Fetching news...")
        for cat in self.categories:
            threading.Thread(target=self.fetch_category_news, args=(cat,), daemon=True).start()

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, lambda: self.log_label.config(text=f"[{timestamp}] {message}"))

    def fetch_category_news(self, category):
        keyword = category["keyword"]
        self.log(f"Fetching {keyword}...")
        rss_url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ja&gl=JP&ceid=JP:ja"

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)

            # Get entries
            entries = feed.entries[:8] # Top 8 entries per category

            # Sort: Nikkei priority, then date
            entries.sort(key=self.sort_priority, reverse=True)

            self.root.after(0, self.display_category, category, entries)
            self.log(f"Loaded {keyword}")
        except Exception as e:
            self.log(f"Error {keyword}: {e}")
            print(f"Error fetching {keyword}: {e}")

    def sort_priority(self, entry):
        # Priority for Nikkei (日本経済新聞)
        score = 0
        source_title = entry.source.get('title', '')
        if "日本経済新聞" in source_title or "nikkei.com" in entry.link:
            score += 1e12 # High priority

        # Add timestamp for chronological order
        published_parsed = getattr(entry, 'published_parsed', None)
        if published_parsed:
            score += datetime(*published_parsed[:6]).timestamp()

        return score

    def display_category(self, category, entries):
        try:
            # Category Section Frame
            section_frame = tk.Frame(self.scrollable_frame, bg=category["bg_color"], pady=15)
            section_frame.pack(fill="x", expand=True)

            # Header
            header_label = tk.Label(section_frame, text=category["display_name"],
                                    font=self.header_font, bg=category["bg_color"],
                                    fg="#333", pady=10)
            header_label.pack(anchor="w", padx=20)

            for entry in entries:
                self.create_article_card(section_frame, entry, category["bg_color"])
        except Exception as e:
            self.log(f"Display error {category['keyword']}: {e}")

    def create_article_card(self, parent, entry, section_bg):
        card = tk.Frame(parent, bg="white", highlightthickness=1, highlightbackground="#e0e0e0", pady=10, padx=15)
        card.pack(fill="x", padx=20, pady=5)

        # Check if Nikkei
        is_nikkei = "日本経済新聞" in entry.source.get('title', '') or "nikkei.com" in entry.link

        content_frame = tk.Frame(card, bg="white")
        content_frame.pack(side="left", fill="both", expand=True)

        img_container = tk.Frame(card, bg="white")
        img_container.pack(side="right", padx=(10, 0))

        # Title
        title_label = tk.Label(content_frame, text=entry.title, font=self.title_font,
                               bg="white", wraplength=450, justify="left", cursor="hand2", fg="#1a0dab")
        title_label.pack(anchor="w")

        if is_nikkei:
            nikkei_badge = tk.Label(content_frame, text="日経優先", font=(self.base_font, 7, "bold"),
                                   bg="#ff4500", fg="white", padx=5)
            nikkei_badge.pack(anchor="w", pady=(2, 0))
        title_label.bind("<Button-1>", lambda e: webbrowser.open(entry.link))

        # Info (Source and Date)
        info_frame = tk.Frame(content_frame, bg="white")
        info_frame.pack(fill="x", pady=(8, 0))

        source = entry.source.get('title', '不明なソース')
        source_label = tk.Label(info_frame, text=source, font=self.source_font, bg="white", fg="#006621")
        source_label.pack(side="left")

        # Format date
        date_str = ""
        if hasattr(entry, 'published_parsed'):
            dt = datetime(*entry.published_parsed[:6])
            date_str = dt.strftime("%Y/%m/%d %H:%M")
        elif hasattr(entry, 'published'):
            date_str = entry.published

        date_label = tk.Label(info_frame, text=date_str, font=self.date_font, bg="white", fg="#70757a")
        date_label.pack(side="right")

        # Async Thumbnail loading
        threading.Thread(target=self.load_thumbnail, args=(card, img_container, entry.link), daemon=True).start()

    def load_thumbnail(self, card, container, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            res = requests.get(url, headers=headers, timeout=3)
            html = res.text

            # Find og:image
            match = re.search(r'<meta [^>]*property="og:image" [^>]*content="([^"]+)"', html)
            if not match:
                match = re.search(r'<meta [^>]*content="([^"]+)" [^>]*property="og:image"', html)

            if match:
                img_url = match.group(1)
                img_res = requests.get(img_url, headers=headers, timeout=3)
                img_data = img_res.content
                img = Image.open(io.BytesIO(img_data))
                img.thumbnail((80, 80))

                # ImageTk.PhotoImage must be created in the main thread or it might be flaky
                self.root.after(0, self.update_card_image, card, container, img)
        except:
            pass # Ignore errors for thumbnails

    def update_card_image(self, card, container, pil_img):
        try:
            photo = ImageTk.PhotoImage(pil_img)
            # Keep a reference to prevent garbage collection
            if not hasattr(card, 'images'):
                card.images = []
            card.images.append(photo)

            img_label = tk.Label(container, image=photo, bg="white")
            img_label.pack()
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    # Set app icon if needed, here we just set title
    app = NewsGadget(root)

    # Simple dependency check on startup
    print("Checking dependencies...")
    try:
        import PIL
        import feedparser
        import requests
        print("All dependencies are present.")
    except ImportError as e:
        print(f"Missing dependency: {e}")

    root.mainloop()
