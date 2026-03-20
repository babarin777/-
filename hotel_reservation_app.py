import streamlit as st
import datetime
import time
import asyncio
import json
import sys
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# --- Page Setup ---
st.set_page_config(page_title="宿泊予約自動実行アプリ", layout="wide")

# --- Japanese Date Helpers ---
JP_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

def format_date_jp(d):
    if not d: return "未設定"
    if isinstance(d, datetime.datetime):
        d = d.date()
    return f"{d.year}年{d.month:02d}月{d.day:02d}日({JP_WEEKDAYS[d.weekday()]})"

def format_time_jp(t):
    if not t: return "未設定"
    return t.strftime("%H時%M分")

# --- Session State Initialization ---
if "running" not in st.session_state:
    st.session_state.running = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "logs" not in st.session_state:
    st.session_state.logs = []

def add_log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")

# --- Header ---
st.title("🏨 宿泊予約自動実行アプリ (安全停止対応版)")
st.markdown("設定した時間に予約サイトへアクセスし、自動で情報を入力します。")

# --- Personal Information (Fixed) ---
PERSONAL_INFO = {
    "name": "馬場光浩",
    "name_kana": "ばばみつひろ",
    "email": "babarin777@gmail.com",
    "phone": "080-8893-4716",
    "zip": "270-0034",
    "address": "千葉県松戸市新松戸３－１－２－６２２"
}

# --- Sidebar: Constant Info & Advanced Settings ---
with st.sidebar:
    st.header("👤 代表者情報")
    st.info(f"""
    **お名前:** {PERSONAL_INFO['name']} ({PERSONAL_INFO['name_kana']})
    **メール:** {PERSONAL_INFO['email']}
    **電話:** {PERSONAL_INFO['phone']}
    **住所:** {PERSONAL_INFO['address']}
    """)

    st.divider()
    st.header("🛠️ 詳細設定")
    retry_duration_hours = st.slider("最大リトライ継続時間 (時間)", 0.5, 4.0, 2.0, 0.5)
    custom_selectors_input = st.text_area("カスタムCSSセレクタ (JSON)", value="{}", help="自動入力が失敗する場合にCSSセレクタを指定できます。")

    if st.button("ログをクリア"):
        st.session_state.logs = []
        st.rerun()

# --- Main Columns ---
col_cfg, col_confirm = st.columns([1.2, 1])

with col_cfg:
    st.subheader("⚙️ 予約・スケジュール設定")

    target_url = st.text_input("1. アクセスするサイトURL",
                               placeholder="https://example.com/reserve",
                               value="http://localhost:8000" if "jules" in sys.executable.lower() else "")

    c1, c2 = st.columns(2)
    with c1:
        st.caption("📅 カレンダー (月 火 水 木 金 土 日)")
        stay_date = st.date_input("2. 宿泊希望日", datetime.date.today() + datetime.timedelta(days=7), label_visibility="collapsed")
        st.markdown(f"**選択中:** {format_date_jp(stay_date)}")
    with c2:
        num_guests = st.number_input("3. 利用人数", min_value=1, value=1, step=1, on_change=None)

    companion_names = st.text_area("4. 同行者名 (改行区切り)", placeholder="同行者1\n同行者2", height=100, on_change=None)

    st.divider()
    st.subheader("⏰ 実行開始タイマー")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        st.caption("📅 実行日")
        exec_date = st.date_input("実行日ラベル", datetime.date.today(), label_visibility="collapsed")
    with e_col2:
        st.caption("⌚ 実行時刻 (HH:MM形式)")
        exec_time_str = st.text_input("実行時刻ラベル", value="00:00", placeholder="例: 10:00", label_visibility="collapsed")

    # 時刻のバリデーション
    try:
        t_parts = exec_time_str.replace("：", ":").split(":")
        exec_time = datetime.time(int(t_parts[0]), int(t_parts[1]))
    except:
        st.error("❌ 実行時刻の形式が正しくありません (例: 08:30)")
        exec_time = datetime.time(0, 0)

    scheduled_datetime = datetime.datetime.combine(exec_date, exec_time)

    st.warning(f"**予定時刻:** {format_date_jp(exec_date)} {format_time_jp(exec_time)}")
    st.caption("※予約開始の数分前に設定することをお勧めします。")

with col_confirm:
    st.subheader("✅ 最終確認パネル")

    # ユーザーが変更した際、即座に視覚的に目立つようにカード形式で表示
    confirmation_html = f"""
    <div style="background-color: #fff2f2; padding: 20px; border-radius: 10px; border: 2px solid #ff4b4b; margin-bottom: 10px;">
        <h3 style="margin-top:0; color: #ff4b4b;">⚠ 予約内容の確認</h3>
        <p style="font-size: 1.2em; margin: 5px 0;">📅 <b>宿泊日:</b> <span style="color:red; font-weight:bold;">{format_date_jp(stay_date)}</span></p>
        <p style="font-size: 1.2em; margin: 5px 0;">👥 <b>人数:</b> <span style="color:red; font-weight:bold;">{num_guests}名</span></p>
        <p style="font-size: 1.0em; margin: 5px 0; color: #555;">🔗 <b>URL:</b> {target_url[:50] + "..." if len(target_url) > 50 else target_url}</p>
        <hr style="margin: 10px 0; border: 0; border-top: 1px solid #ccc;">
        <p style="font-size: 1.1em; margin: 5px 0;">⏰ <b>実行開始:</b> {format_date_jp(scheduled_datetime)} {format_time_jp(exec_time)}</p>
        <p style="font-size: 1.0em; margin: 5px 0;">👤 <b>代表者:</b> {PERSONAL_INFO['name']} 様</p>
    </div>
    """
    st.markdown(confirmation_html, unsafe_allow_html=True)

    st.info("💡 **ヒント:** 入力値を変更した後、**[Enter]キー**を押すか**入力欄の外をクリック**すると、上の確認パネルが更新されます。")

    # --- Control Buttons ---
    if not st.session_state.running:
        if st.button("🚀 上記の内容で実行予約（待機開始）", use_container_width=True, type="primary"):
            if not target_url:
                st.error("サイトURLを入力してください。")
            elif ":" not in exec_time_str:
                st.error("実行時刻を正しく入力してください。")
            else:
                st.session_state.running = True
                st.session_state.stop_requested = False
                st.session_state.logs = []
                add_log("実行待機を開始しました。")
                st.rerun()
    else:
        # Stop Button (Highly visible)
        st.error("⚠️ 自動実行中...")
        if st.button("🛑 実行を強制中断（ブラウザを閉じる）", use_container_width=True):
            st.session_state.stop_requested = True
            st.session_state.running = False # 即座にフラグを落とす
            add_log("ユーザーにより中断リクエストが送信されました。")
            st.rerun()

# --- Status and Reason Display (Traceback replacement) ---
st.divider()
status_placeholder = st.empty()
error_display_placeholder = st.empty()

# 実行中でない場合でも、停止理由などがあれば表示
if not st.session_state.running and st.session_state.logs:
    last_log = st.session_state.logs[-1]
    if "エラー" in last_log or "中断" in last_log or "失敗" in last_log:
        error_display_placeholder.error(f"📋 直近の停止理由: {last_log}")

# --- Log Area ---
if st.session_state.running or st.session_state.logs:
    with st.expander("📝 実行ログ・履歴", expanded=st.session_state.running):
        log_placeholder = st.empty()
        def update_log_ui():
            log_placeholder.markdown("\n".join([f"- {l}" for l in st.session_state.logs[::-1]]))
        update_log_ui()

# --- Core Logic ---
if st.session_state.running:
    async def fill_form(page, reservation_details):
        def log(m): add_log(m)
        info = PERSONAL_INFO

        # Custom selectors
        try:
            custom_map = json.loads(custom_selectors_input)
            for selector, val in custom_map.items():
                try: await page.fill(selector, str(val)); log(f"カスタム入力: {selector}")
                except: pass
        except: pass

        async def attempt_fill(kws, val):
            for kw in kws:
                try:
                    # Common input types
                    selectors = [f"input[placeholder*='{kw}']", f"input[name*='{kw}']", f"input[id*='{kw}']", f"textarea[name*='{kw}']"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible() and not (await el.input_value()):
                            await el.fill(val); log(f"入力成功: {kw}"); return True
                    # Labels
                    labels = await page.query_selector_all("label")
                    for label in labels:
                        if kw in (await label.inner_text()):
                            for_id = await label.get_attribute("for")
                            if for_id:
                                el = await page.query_selector(f"#{for_id}")
                                if el and not (await el.input_value()):
                                    await el.fill(val); log(f"入力成功(ラベル): {kw}"); return True
                except: continue
            return False

        log("フォームへの自動入力を開始します...")
        # Name handling
        if not await attempt_fill(["氏名", "お名前", "名前", "name"], info["name"]):
            await attempt_fill(["姓", "名字", "苗字"], info["name"][:2])
            await attempt_fill(["名"], info["name"][2:])
        # Kana handling
        if not await attempt_fill(["カナ", "かな", "ふりがな", "kana"], info["name_kana"]):
            await attempt_fill(["せい", "セイ", "姓カナ"], info["name_kana"][:2])
            await attempt_fill(["めい", "メイ", "名カナ"], info["name_kana"][2:])

        await attempt_fill(["メール", "email", "mail"], info["email"])
        await attempt_fill(["電話", "tel", "phone"], info["phone"])
        await attempt_fill(["郵便番号", "zip"], info["zip"])
        await attempt_fill(["住所", "address"], info["address"])
        await attempt_fill(["人数", "宿泊人数", "guest"], str(num_guests))

        # Date fill
        await attempt_fill(["宿泊日", "到着日", "チェックイン", "date"], stay_date.strftime("%Y-%m-%d"))

        if companion_names:
            await attempt_fill(["同行者", "備考", "remark"], companion_names)

        log("自動入力が完了しました。")

    async def main_loop():
        # 1. Wait for time
        now = datetime.datetime.now()
        if scheduled_datetime > now:
            wait_sec = (scheduled_datetime - now).total_seconds()
            status_placeholder.warning(f"🕒 開始待機中... ({format_time_jp(exec_time)} 開始予定)")
            pbar = st.progress(0)
            for i in range(int(wait_sec)):
                if st.session_state.stop_requested: break
                time.sleep(1)
                pbar.progress(min(1.0, (i+1)/wait_sec))
                if i % 10 == 0: status_placeholder.warning(f"🕒 開始まであと {int(wait_sec - i)} 秒...")
            if st.session_state.stop_requested:
                st.session_state.running = False
                st.session_state.stop_requested = False
                st.rerun()
            status_placeholder.success("🚀 実行時間になりました！")

        # 2. Browser Loop
        end_time = datetime.datetime.now() + datetime.timedelta(hours=retry_duration_hours)
        async with async_playwright() as p:
            is_jules = "jules" in sys.executable.lower() or "/home/jules" in sys.executable.lower()
            try:
                browser = await p.chromium.launch(headless=is_jules, channel="chrome" if not is_jules else None)
            except:
                browser = await p.chromium.launch(headless=True if is_jules else False)

            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36")
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            attempt = 0
            while datetime.datetime.now() < end_time:
                if st.session_state.stop_requested: break
                attempt += 1
                status_placeholder.info(f"🔄 試行 {attempt} 回目: アクセス中... (残り時間: {str(end_time - datetime.datetime.now()).split('.')[0]})")

                try:
                    res = await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                    if res and (res.status >= 500 or res.status == 429):
                        add_log(f"サーバー混雑 (Status {res.status})。再試行します。")
                        await asyncio.sleep(5); continue

                    content = await page.content()
                    if any(kw in content for kw in ["メンテナンス", "混み合って", "アクセスが集中"]):
                        add_log("混雑画面を検出。5秒待機します。")
                        await asyncio.sleep(5); continue

                    # Search for input fields
                    found = False
                    for _ in range(10):
                        if st.session_state.stop_requested: break
                        if await page.query_selector("input"): found = True; break
                        await asyncio.sleep(1)

                    if found:
                        add_log("予約フォームを検出しました。")
                        await fill_form(page, {"stay_date": stay_date, "num_guests": num_guests})

                        if is_jules:
                            await page.screenshot(path="/home/jules/verification/filled_form_v3_fixed.png")
                            await browser.close()
                            st.session_state.running = False
                            return

                        status_placeholder.success("✨ 自動入力完了！内容を確認して予約を確定させてください。")
                        add_log("ブラウザを開いたまま待機します。")
                        while not page.is_closed():
                            if st.session_state.stop_requested: break
                            await asyncio.sleep(1)
                        break
                    else:
                        add_log("フォームが見つかりません。リロードします。")
                except Exception as e:
                    add_log(f"エラー: {str(e).splitlines()[0]}")

                await asyncio.sleep(3)

            await browser.close()
            st.session_state.running = False
            st.session_state.stop_requested = False
            st.rerun()

    try:
        asyncio.run(main_loop())
    except Exception as e:
        # トレースバックを画面に出さず、ログに記録して状態を戻す
        err_msg = str(e).splitlines()[0]
        add_log(f"システムエラーで停止しました: {err_msg}")
        st.session_state.running = False
        st.rerun()

if __name__ == "__main__":
    import sys
    import streamlit.runtime as st_runtime

    # すでにStreamlit環境下で動いているかチェック
    if st_runtime.exists():
        # メインロジック（上の st.title 等）は自動で実行されるため、ここでは何もしない
        pass
    else:
        # python hotel_reservation_app.py として直接実行された場合、
        # 内部的に streamlit run を呼び出してブラウザを起動する
        from streamlit.web import cli as stcli
        port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
        sys.argv = ["streamlit", "run", sys.argv[0], f"--server.port={port}", "--server.address=0.0.0.0"]
        sys.exit(stcli.main())
