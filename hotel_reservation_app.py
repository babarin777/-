import streamlit as st
import datetime
import time
import asyncio
import json
import traceback
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import sys

# Set page config
st.set_page_config(page_title="宿泊予約自動実行アプリ (高負荷対応版)", layout="wide")

st.title("宿泊予約自動実行アプリ (高負荷対応版)")
st.write("指定したサイトに指定した時間にアクセスし、予約を完了するまで最大2時間リトライを続けます。")

# Personal Information (Fixed)
PERSONAL_INFO = {
    "name": "馬場光浩",
    "name_kana": "ばばみつひろ",
    "email": "babarin777@gmail.com",
    "phone": "080-8893-4716",
    "zip": "270-0034",
    "address": "千葉県松戸市新松戸３－１－２－６２２"
}

# --- Layout ---
col_left, col_right = st.columns([1, 2])

with col_left:
    st.header("⚙️ 設定項目")
    target_url = st.text_input("アクセスするサイトURL", placeholder="https://example.com/reserve", value="http://localhost:8000" if "jules" in sys.executable.lower() else "")
    stay_date = st.date_input("宿泊希望日", datetime.date.today() + datetime.timedelta(days=7))
    num_guests = st.number_input("利用人数", min_value=1, value=1)
    companion_names = st.text_area("同行者名（改行区切り）", placeholder="同行者1\n同行者2")

    st.divider()
    st.subheader("⏰ 実行スケジュールの設定")
    exec_date = st.date_input("実行日", datetime.date.today())
    exec_time = st.time_input("実行時間", datetime.time(0, 0))
    scheduled_datetime = datetime.datetime.combine(exec_date, exec_time)
    st.info(f"予定日時: {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}")

    st.divider()
    st.subheader("🛠️ 詳細設定")
    retry_duration_hours = st.slider("最大リトライ継続時間 (時間)", 0.5, 4.0, 2.0, 0.5)
    custom_selectors_input = st.text_area("カスタムCSSセレクタ (JSON)", value="{}")

with col_right:
    with st.expander("📖 動作説明・マニュアル (必ずお読みください)", expanded=False):
        st.markdown("""
        ### 1. 準備
        このアプリを動かすには、Python環境と以下のライブラリが必要です。
        - `pip install streamlit playwright playwright-stealth`
        - `playwright install chromium` (初回のみ実行)

        ### 2. 設定項目
        - **サイトURL**: 予約フォームのURL、またはその直前のページを指定してください。
        - **宿泊情報**: 人数や同行者名を入力します。

        ### 3. 動作の流れ
        1. 「待機開始」ボタンを押すと、指定時間までカウントダウンします。
        2. 時間になるとブラウザ(Chrome優先)が起動し、サイトへアクセスを試みます。
        3. **高負荷対策**: サイトが混雑して繋がらない場合やエラーが出た場合、自動でリトライを繰り返します。
        4. フォームが見つかったら、馬場様の情報を自動入力します。
        5. **完了確認**: 入力後、ブラウザは開いたままになります。最後の「予約確定」ボタンなどは、内容を最終確認した上でご自身で押してください。
        """)

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.subheader("👤 入力される個人情報")
        st.json(PERSONAL_INFO)
    with col_info2:
        st.subheader("🏨 予約内容")
        st.write(f"**宿泊日:** {stay_date}")
        st.write(f"**人数:** {num_guests}名")
        st.write(f"**同行者:** {companion_names if companion_names else 'なし'}")

    st.divider()
    status_area = st.empty()
    log_area = st.expander("詳細ログ", expanded=True)

    # Move logic outside the button block to keep state
    if st.button("🚀 待機開始 / 実行", use_container_width=True, key="main_start_button"):
        if not target_url:
            st.error("URLを入力してください。")
        else:
            now = datetime.datetime.now()
            if scheduled_datetime > now:
                wait_seconds = (scheduled_datetime - now).total_seconds()
                st.warning(f"実行時間まで待機します...")
                pbar = st.progress(0)
                st_rem = st.empty()
                for i in range(int(wait_seconds)):
                    time.sleep(1)
                    rem = int(wait_seconds - i)
                    pbar.progress((i+1)/wait_seconds)
                    st_rem.text(f"開始まであと {rem} 秒...")
                    if rem <= 0: break
                st.success("実行時間になりました！")

            # Start loop
            async def fill_form_best_effort(page, info, reservation_details, custom_selectors_json, log_container):
                def log(msg): log_container.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")
                try:
                    custom_map = json.loads(custom_selectors_json)
                    for selector, val in custom_map.items():
                        try:
                            await page.fill(selector, str(val))
                            log(f"✅ カスタムセレクタ '{selector}' に入力")
                        except: pass
                except: pass

                async def fill_field(keywords, value):
                    for kw in keywords:
                        try:
                            selectors = [f"input[placeholder*='{kw}']", f"input[name*='{kw}']", f"input[id*='{kw}']", f"textarea[name*='{kw}']"]
                            for sel in selectors:
                                el = await page.query_selector(sel)
                                if el and await el.is_visible() and not (await el.input_value()):
                                    await el.fill(value)
                                    log(f"✅ '{kw}' 相当のフィールドに入力")
                                    return True
                            labels = await page.query_selector_all("label")
                            for label in labels:
                                if kw in (await label.inner_text()):
                                    for_id = await label.get_attribute("for")
                                    if for_id:
                                        el = await page.query_selector(f"#{for_id}")
                                        if el and not (await el.input_value()):
                                            await el.fill(value)
                                            log(f"✅ ラベル '{kw}' に基づき入力")
                                            return True
                        except: continue
                    return False

                log("フォーム入力を開始...")
                if not await fill_field(["氏名", "お名前", "名前", "name"], info["name"]):
                    await fill_field(["姓", "名字", "苗字"], info["name"][0:2])
                    await fill_field(["名"], info["name"][2:])
                if not await fill_field(["カナ", "かな", "ふりがな", "kana"], info["name_kana"]):
                    await fill_field(["せい", "セイ", "姓カナ"], info["name_kana"][0:2])
                    await fill_field(["めい", "メイ", "名カナ"], info["name_kana"][2:])
                await fill_field(["メール", "email", "mail"], info["email"])
                await fill_field(["電話", "tel", "phone"], info["phone"])
                await fill_field(["郵便番号", "zip"], info["zip"])
                await fill_field(["住所", "address"], info["address"])
                await fill_field(["人数", "宿泊人数"], str(reservation_details["num_guests"]))
                if reservation_details["companions"]:
                    await fill_field(["同行者", "備考", "remark"], reservation_details["companions"])

            async def run_reservation_loop(url, info, reservation_details, max_hours):
                end_time = datetime.datetime.now() + datetime.timedelta(hours=max_hours)
                async with async_playwright() as p:
                    try:
                        is_jules = "jules" in sys.executable.lower() or "/home/jules" in sys.executable.lower()
                        browser = await p.chromium.launch(headless=is_jules, channel="chrome" if not is_jules else None)
                    except:
                        browser = await p.chromium.launch(headless=True if is_jules else False)
                    context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36")
                    page = await context.new_page()
                    # Apply stealth
                    stealth_obj = Stealth()
                    await stealth_obj.apply_stealth_async(page)

                    attempt = 0
                    while datetime.datetime.now() < end_time:
                        attempt += 1
                        current_time = datetime.datetime.now().strftime('%H:%M:%S')
                        remaining = str(end_time - datetime.datetime.now()).split('.')[0]
                        status_area.info(f"試行 {attempt} 回目: アクセス中... (時刻: {current_time}, 残り時間: {remaining})")
                        try:
                            response = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                            if response and (response.status >= 500 or response.status == 429):
                                with log_area: st.error(f"[{current_time}] サーバーが混雑しています (Status: {response.status})。再試行します。")
                                await asyncio.sleep(2); continue
                            elif response and response.status >= 400:
                                with log_area: st.warning(f"[{current_time}] エラー応答 (Status: {response.status})。")
                            content = await page.content()
                            if "メンテナンス中" in content or "ただいま混み合っております" in content:
                                with log_area: st.warning(f"[{current_time}] 混雑/メンテナンス画面を検出。")
                                await asyncio.sleep(5); continue
                            found_form = False
                            for _ in range(15):
                                if (await page.query_selector("input")):
                                    found_form = True; break
                                await asyncio.sleep(1)
                            if found_form:
                                with log_area: st.success(f"[{current_time}] 予約フォームを検出。入力開始。")
                                await fill_form_best_effort(page, info, reservation_details, custom_selectors_input, log_area)
                                status_area.success("自動入力が完了しました！内容を確認して予約を確定させてください。")
                                if is_jules:
                                    # Verification environment: take a screenshot of the filled form before closing
                                    await page.screenshot(path="/home/jules/verification/filled_form.png")
                                    await browser.close()
                                    return
                                # Local environment: keep browser open for user confirmation
                                while not page.is_closed():
                                    try:
                                        await asyncio.sleep(1)
                                    except:
                                        break
                                return
                            else:
                                with log_area: st.warning(f"[{current_time}] フォーム未検出。リロード。")
                        except Exception as e:
                            with log_area: st.warning(f"[{current_time}] アクセス失敗: {str(e).splitlines()[0]}")
                        await asyncio.sleep(2)
                    status_area.error("制限時間内に予約を完了できませんでした。")

            asyncio.run(run_reservation_loop(target_url, PERSONAL_INFO, {
                "stay_date": stay_date,
                "num_guests": num_guests,
                "companions": companion_names
            }, retry_duration_hours))
