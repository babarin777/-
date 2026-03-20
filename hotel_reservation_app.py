import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import asyncio
import datetime
import time
import threading
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import json
import os
import sys

# --- Fix for NotImplementedError on Windows ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Try to import openai, install if missing
try:
    import openai
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    import openai

# --- Configuration & Constants ---
DEFAULT_INFO = {
    "representative": "馬場光浩（ばばみつひろ）",
    "email": "babarin777@gmail.com",
    "tel": "080-8893-4716",
    "address": "〒270-0034 千葉県松戸市新松戸３－１－２－６２２",
}

JP_WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"]
RETRY_DURATION = datetime.timedelta(hours=2)

def format_date_jp(d):
    if d is None: return ""
    idx = (d.weekday() + 1) % 7
    return d.strftime(f"%Y/%m/%d({JP_WEEKDAYS[idx]})")

# --- Reservation Manager Class ---
class ReservationManager:
    def __init__(self):
        self.logs = []
        self.running = False
        self.stop_requested = False
        self.awaiting_input = False
        self.missing_items = []
        self.missing_values = {}
        self.input_ready_event = threading.Event()
        self.success = False
        self.error = None
        self.thread = None

    def add_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")

    def start(self, args):
        self.logs = []
        self.running = True
        self.stop_requested = False
        self.awaiting_input = False
        self.missing_items = []
        self.missing_values = {}
        self.input_ready_event.clear()
        self.success = False
        self.error = None

        ctx = get_script_run_ctx()
        self.thread = threading.Thread(target=self._run_wrapper, args=(args, ctx))
        add_script_run_ctx(self.thread, ctx)
        self.thread.start()

    def stop(self):
        self.stop_requested = True
        self.input_ready_event.set()

    def _run_wrapper(self, args, ctx):
        if ctx: add_script_run_ctx(threading.current_thread(), ctx)
        if sys.platform == 'win32':
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.main_loop(*args))
        except Exception as e:
            self.add_log(f"システムエラー: {str(e)}")
            self.error = str(e)
        finally:
            self.running = False
            loop.close()

    async def get_gpt_mapping(self, api_key, html_context, items_to_fill, search_submit=False):
        client = openai.OpenAI(api_key=api_key)
        prompt = f"""
以下のHTML構造を持つ宿泊予約サイトの入力フォームがあります。
これらの項目を入力するために、対応するHTML要素のCSSセレクタを特定してください。

【入力項目】
{json.dumps(items_to_fill, ensure_ascii=False, indent=2)}
{"【追加指示】予約を確定させるための「送信」「予約確定」「次へ」ボタンなどのCSSセレクタも特定し 'submit_button' というキーで返してください。" if search_submit else ""}

【HTML構造の一部】
{html_context}

【回答形式】
JSON形式で回答してください。
{{
  "mappings": {{
    "項目名": "CSSセレクタ",
    "submit_button": "CSSセレクタ"
  }},
  "missing_info": ["サイト側で入力を求められているが、上記入力項目に存在しない重要な項目があればリストアップしてください（例：チェックイン時間、性別など）"]
}}
CSSセレクタは、id、name、または一意に特定できる組合せを使用してください。
見つからない項目は含めないでください。
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.add_log(f"GPT連携エラー: {e}")
            return {"mappings": {}, "missing_info": []}

    async def fill_and_submit(self, page, api_key, data_map, auto_confirm):
        self.add_log("フォーム解析中...")

        elements = await page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input, select, textarea, button, a.btn, .button'));
                return inputs.map(el => {
                    let label = "";
                    if (el.id) {
                        const l = document.querySelector(`label[for="${el.id}"]`);
                        if (l) label = l.innerText;
                    }
                    if (!label) {
                        label = el.closest('label')?.innerText || el.placeholder || el.innerText || el.name || "";
                    }
                    const context = el.parentElement?.innerText?.substring(0, 50) || "";
                    return {
                        tag: el.tagName,
                        type: el.type,
                        name: el.name,
                        id: el.id,
                        label: label.trim().substring(0, 100),
                        context: context.trim().substring(0, 100),
                        placeholder: el.placeholder
                    };
                }).filter(e => e.label || e.name || e.id);
            }
        """)

        html_context = json.dumps(elements, ensure_ascii=False, indent=2)
        mapping_res = await self.get_gpt_mapping(api_key, html_context, data_map, search_submit=True)
        mappings = mapping_res.get("mappings", {})
        missing = mapping_res.get("missing_info", [])

        if missing:
            self.add_log(f"不足情報の入力を待機中: {', '.join(missing)}")
            self.missing_items = missing
            self.awaiting_input = True
            self.input_ready_event.clear()
            while self.awaiting_input and not self.stop_requested:
                await asyncio.sleep(1)
                if self.input_ready_event.is_set(): break
            if self.stop_requested: return False
            data_map.update(self.missing_values)
            mapping_res = await self.get_gpt_mapping(api_key, html_context, data_map, search_submit=True)
            mappings = mapping_res.get("mappings", {})

        # Fill fields
        for item, value in data_map.items():
            selector = mappings.get(item)
            if selector:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    el = await page.query_selector(selector)
                    tag = await el.evaluate("el => el.tagName")
                    if tag == "SELECT":
                        await page.select_option(selector, label=str(value))
                    elif tag == "INPUT" and (await el.get_attribute("type")) in ["checkbox", "radio"]:
                        await page.check(selector)
                    else:
                        await page.fill(selector, str(value))
                    self.add_log(f"入力完了: {item}")
                except:
                    self.add_log(f"入力失敗: {item}")

        if auto_confirm:
            submit_selector = mappings.get("submit_button")
            if submit_selector:
                self.add_log("予約確定ボタンをクリックします...")
                try:
                    await page.click(submit_selector)
                    # Use both networkidle and a small wait to be safe
                    try: await page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass

                    # Heuristic check for success
                    final_content = await page.content()
                    success_keywords = ["完了", "確定しました", "予約を受け付けました", "予約番号", "Success", "Complete"]
                    if any(kw in final_content for kw in success_keywords):
                        self.add_log("【成功】予約完了が確認されました。")
                    else:
                        self.add_log("予約確定ボタンを押しました。完了画面を確認してください。")
                    return True
                except Exception as e:
                    self.add_log(f"確定ボタンのクリックに失敗しました: {e}")
                    return False # Retry if click failed due to navigation/closed
            else:
                self.add_log("確定ボタンが見つかりませんでした。手動で操作してください。")
                return True # Consider filled, but manual confirmation needed

        self.add_log("自動確定がOFFのため、入力のみ完了しました。手動で予約を確定してください。")
        return True

    async def main_loop(self, url, api_key, exec_dt, stay_date, stay_count, adult_count, child_count, companion_name, auto_confirm):
        self.add_log(f"待機開始: {exec_dt.strftime('%H:%M:%S')} に開始します")

        while datetime.datetime.now() < exec_dt:
            if self.stop_requested:
                self.add_log("停止されました。")
                return
            await asyncio.sleep(1)

        exec_start_time = datetime.datetime.now()
        retry_count = 0

        async with async_playwright() as p:
            browser = None
            context = None
            page = None

            while datetime.datetime.now() < exec_start_time + RETRY_DURATION:
                if self.stop_requested: break

                # Check if browser/page is healthy, recreate if needed
                if not browser or page.is_closed():
                    if browser:
                        try: await browser.close()
                        except: pass
                    self.add_log("ブラウザを起動します...")
                    browser = await p.chromium.launch(headless=False, channel="chrome")
                    if not browser: browser = await p.chromium.launch(headless=False)
                    context = await browser.new_context()
                    page = await context.new_page()
                    await stealth_async(page)

                try:
                    retry_count += 1
                    self.add_log(f"アクセス試行 #{retry_count}...")
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    if response.status >= 500:
                        self.add_log(f"サーバーエラー ({response.status})。再試行します。")
                        await asyncio.sleep(5)
                        continue

                    content = await page.content()
                    busy_keywords = ["混雑", "アクセス集中", "しばらくお待ちください", "Busy", "Maintenance"]
                    if any(kw in content for kw in busy_keywords):
                        self.add_log("サイトが混雑しています。再試行します。")
                        await asyncio.sleep(5)
                        continue

                    data_map = {
                        "宿泊日": format_date_jp(stay_date),
                        "宿泊数": f"{stay_count}泊",
                        "大人人数": f"{adult_count}名",
                        "子供人数": f"{child_count}名",
                        "利用代表者": DEFAULT_INFO["representative"],
                        "メールアドレス": DEFAULT_INFO["email"],
                        "電話番号": DEFAULT_INFO["tel"],
                        "住所": DEFAULT_INFO["address"],
                        "同行者名": companion_name
                    }

                    success = await self.fill_and_submit(page, api_key, data_map, auto_confirm)
                    if success:
                        self.success = True
                        self.add_log("情報の入力処理が正常に完了しました。")
                        # Keep open
                        while not self.stop_requested:
                            await asyncio.sleep(2)
                            if page.is_closed(): break
                        break

                except Exception as e:
                    self.add_log(f"アクセス失敗: {e}。再試行します。")
                    await asyncio.sleep(5)

            if not self.success and not self.stop_requested:
                self.add_log("2時間の制限時間を経過しました。終了します。")

            await browser.close()

# --- Streamlit UI ---
st.set_page_config(page_title="宿泊予約自動化くん", layout="wide")

if "manager" not in st.session_state:
    st.session_state.manager = ReservationManager()

manager = st.session_state.manager

st.title("🏨 宿泊予約自動化アプリ")
st.caption("混雑するサイトに粘り強くアクセスし、予約を完成させます。")

with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("OpenAI API Key", type="password", key="openai_api_key")
    auto_confirm = st.checkbox("自動で予約確定まで行う", value=False, help="チェックを入れると、情報の入力後に「予約確定」ボタンを自動でクリックします。")

    st.divider()
    st.subheader("代表者情報 (固定)")
    st.text(f"氏名: {DEFAULT_INFO['representative']}")
    st.text(f"Email: {DEFAULT_INFO['email']}")
    st.text(f"TEL: {DEFAULT_INFO['tel']}")
    st.text(f"住所: {DEFAULT_INFO['address']}")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 予約条件")
    url = st.text_input("アクセスするサイトURL", placeholder="https://example.com/reserve", key="input_url")
    c1, c2 = st.columns(2)
    stay_date = c1.date_input("宿泊希望日", datetime.date.today() + datetime.timedelta(days=7), key="stay_date")
    stay_count = c2.number_input("宿泊数", min_value=1, value=1, key="stay_count")
    c3, c4 = st.columns(2)
    adult_count = c3.number_input("大人人数", min_value=1, value=1, key="adult_count")
    child_count = c4.number_input("子供人数", min_value=0, value=0, key="child_count")
    companion_name = st.text_input("同行者名 (複数いる場合はカンマ区切り)", key="companion_name")

    st.divider()
    st.subheader("⏰ 実行タイミング")
    exec_date = st.date_input("実行日", datetime.date.today(), key="exec_date")
    exec_time_str = st.text_input("実行時間 (HH:MM)", value="10:00", key="exec_time")
    try:
        h, m = map(int, exec_time_str.split(":"))
        exec_dt = datetime.datetime.combine(exec_date, datetime.time(h, m))
    except:
        st.error("時間の形式が正しくありません (HH:MM)")
        exec_dt = None

with col2:
    st.subheader("📋 最終確認")
    with st.container(border=True):
        st.write(f"**サイト:** {url if url else '(未入力)'}")
        st.write(f"**実行時刻:** {exec_dt.strftime('%Y/%m/%d %H:%M') if exec_dt else '(エラー)'}")
        st.write(f"**自動確定:** {'ON (自動送信あり)' if auto_confirm else 'OFF (入力のみ)'}")
        st.divider()
        cols = st.columns(7)
        for i, wd in enumerate(JP_WEEKDAYS):
            cols[i].markdown(f"<center><b>{wd}</b></center>", unsafe_allow_html=True)
        st.write(f"**宿泊日:** {format_date_jp(stay_date)} から {stay_count} 泊")
        st.write(f"**人数:** 大人{adult_count}名 / 子供{child_count}名")
        st.write(f"**同行者:** {companion_name if companion_name else 'なし'}")

    st.divider()
    if not manager.running:
        if st.button("🚀 予約実行 (待機開始)", use_container_width=True, type="primary"):
            if not api_key: st.error("APIキーが必要です")
            elif not url: st.error("URLが必要です")
            elif not exec_dt: st.error("実行時間を正しく入力してください")
            else:
                manager.start((url, api_key, exec_dt, stay_date, stay_count, adult_count, child_count, companion_name, auto_confirm))
                st.rerun()
    else:
        if st.button("⏹️ 停止", use_container_width=True):
            manager.stop()
            st.rerun()

if manager.awaiting_input:
    st.warning("⚠️ サイト側で追加の情報が必要です。以下を入力してください。")
    with st.form("missing_info_form"):
        new_values = {}
        for item in manager.missing_items:
            new_values[item] = st.text_input(item)
        if st.form_submit_button("入力を完了して続行"):
            manager.missing_values = new_values
            manager.awaiting_input = False
            manager.input_ready_event.set()
            st.rerun()

st.divider()
st.subheader("🚩 実行ログ")
log_area = st.empty()
with log_area.container():
    if not manager.logs:
        st.info("実行ボタンを押すとログが表示されます。混雑時は最大2時間粘り強くリトライします。")
    else:
        for log in reversed(manager.logs):
            st.text(log)

if manager.running:
    time.sleep(2)
    st.rerun()

# --- Launcher for direct execution ---
if __name__ == "__main__":
    from streamlit.web import cli as stcli
    from streamlit.runtime import exists
    if not exists():
        sys.argv = ["streamlit", "run", sys.argv[0]] + sys.argv[1:]
        sys.exit(stcli.main())
