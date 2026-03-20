import streamlit as st
import datetime
import time
import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import stealth
import sys

# Set page config
st.set_page_config(page_title="宿泊予約自動実行アプリ", layout="wide")

st.title("宿泊予約自動実行アプリ")
st.write("指定したサイトに指定した時間にアクセスし、予約情報を入力します。")

with st.expander("使い方ガイド"):
    st.markdown("""
    1. **設定項目**を入力します。
       - アクセスするサイトのURL（予約フォームの直前、または予約フォームのURL）
       - 宿泊日、人数、同行者名
       - 実行スケジュール（いつブラウザを起動して入力を開始するか）
    2. **待機開始**ボタンを押します。
       - 指定した時間までカウントダウンが始まります。
       - すぐに試したい場合は、実行時間を現在の時刻より前に設定してください。
    3. **ブラウザが起動**します。
       - URLにアクセスします。
       - ページ内にフォーム（inputタグ）が見つかるまで最大5分間待機します。
       - フォームが見つかると、馬場様の情報を自動的に入力します。
    4. **手動で確認・確定**
       - 自動入力が完了したら、内容を確認し、不足があれば補完して予約を完了させてください。
       - クレジットカード情報などは安全のため自動入力されません。
    """)

# Personal Information (Fixed)
PERSONAL_INFO = {
    "name": "馬場光浩",
    "name_kana": "ばばみつひろ",
    "email": "babarin777@gmail.com",
    "phone": "080-8893-4716",
    "zip": "270-0034",
    "address": "千葉県松戸市新松戸３－１－２－６２２"
}

# User Inputs
with st.sidebar:
    st.header("設定項目")
    target_url = st.text_input("アクセスするサイトURL", placeholder="https://example.com/reserve")
    stay_date = st.date_input("宿泊希望日", datetime.date.today() + datetime.timedelta(days=7))
    num_guests = st.number_input("利用人数", min_value=1, value=1)
    companion_names = st.text_area("同行者名（改行区切り）", placeholder="同行者1\n同行者2")

    st.divider()
    st.subheader("実行スケジュールの設定")
    exec_date = st.date_input("実行日", datetime.date.today())
    exec_time = st.time_input("実行時間", datetime.time(21, 0))

    scheduled_datetime = datetime.datetime.combine(exec_date, exec_time)

    st.info(f"実行予定日時: {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}")

# Main UI
col1, col2 = st.columns(2)

with col1:
    st.subheader("入力される個人情報")
    st.json(PERSONAL_INFO)

with col2:
    st.subheader("予約情報")
    st.write(f"**宿泊日:** {stay_date}")
    st.write(f"**人数:** {num_guests}名")
    st.write(f"**同行者:**")
    st.write(companion_names if companion_names else "なし")

    st.divider()
    st.subheader("カスタムCSSセレクタ (上級者向け)")
    custom_selectors = st.text_area("JSON形式で指定 (例: {\"input[name='user_name']\": \"馬場光浩\"})", value="{}")

async def fill_form_best_effort(page, info, reservation_details, custom_selectors_json):
    """
    Attempts to fill common fields using heuristics and custom selectors.
    """

    # Custom selectors first
    try:
        custom_map = json.loads(custom_selectors_json)
        for selector, val in custom_map.items():
            try:
                await page.fill(selector, str(val))
                st.write(f"カスタムセレクタ '{selector}' に入力しました。")
            except:
                st.warning(f"カスタムセレクタ '{selector}' が見つかりませんでした。")
    except Exception as e:
        if custom_selectors_json != "{}":
            st.error(f"カスタムセレクタの解析に失敗しました: {e}")

    # Helper to fill by multiple possible labels/names
    async def fill_field(keywords, value):
        for kw in keywords:
            try:
                # Try by placeholder, label text, or name/id attribute
                selectors = [
                    f"input[placeholder*='{kw}']",
                    f"input[name*='{kw}']",
                    f"input[id*='{kw}']",
                    f"textarea[name*='{kw}']"
                ]
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        # Don't overwrite if already filled by custom selector
                        current_val = await element.input_value()
                        if not current_val:
                            await element.fill(value)
                            st.write(f"フィールド '{kw}' に入力しました。")
                            return True
                        else:
                            return True

                # Try finding by label text association
                labels = await page.query_selector_all("label")
                for label in labels:
                    text = await label.inner_text()
                    if kw in text:
                        for_id = await label.get_attribute("for")
                        if for_id:
                            element = await page.query_selector(f"#{for_id}")
                            if element:
                                current_val = await element.input_value()
                                if not current_val:
                                    await element.fill(value)
                                    st.write(f"ラベル '{text}' に基づき入力しました。")
                                    return True
                                else:
                                    return True
            except:
                continue
        return False

    st.info("汎用的なアルゴリズムでフォームへの自動入力を試行中...")

    # Fill Name
    name_success = await fill_field(["氏名", "お名前", "名前", "name"], info["name"])
    if not name_success:
        # Try split name (Last/First)
        last_name = info["name"][0:2] # Heuristic: Baba
        first_name = info["name"][2:] # Mitsuhiro
        await fill_field(["姓", "名字", "苗字", "lastname", "last_name", "family_name"], last_name)
        await fill_field(["名", "firstname", "first_name", "given_name"], first_name)

    kana_success = await fill_field(["カナ", "かな", "ふりがな", "kana"], info["name_kana"])
    if not kana_success:
        # Try split kana
        last_kana = info["name_kana"][0:2] # ばば
        first_kana = info["name_kana"][2:] # みつひろ
        await fill_field(["せい", "セイ", "姓カナ", "last_kana"], last_kana)
        await fill_field(["めい", "メイ", "名カナ", "first_kana"], first_kana)

    # Fill Email
    await fill_field(["メール", "email", "mail"], info["email"])

    # Fill Phone
    await fill_field(["電話", "tel", "phone"], info["phone"])

    # Fill Zip/Address
    await fill_field(["郵便番号", "zip", "postcode"], info["zip"])
    await fill_field(["住所", "address"], info["address"])

    # Fill Reservation details
    await fill_field(["人数", "宿泊人数", "guest"], str(reservation_details["num_guests"]))
    if reservation_details["companions"]:
        await fill_field(["同行者", "備考", "message", "remark"], reservation_details["companions"])

async def run_reservation(url, info, reservation_details):
    custom_selectors_json = reservation_details.get("custom_selectors", "{}")
    async with async_playwright() as p:
        # Priority for Chrome
        try:
            browser = await p.chromium.launch(headless=False, channel="chrome")
        except:
            st.warning("Chromeが見つかりませんでした。通常のChromiumを使用します。")
            browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await stealth(page)

        st.write(f"URLにアクセス中: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Wait for user to navigate to the actual form if the URL was just a top page
            st.info("予約フォームが表示されるまで待機しています。フォームが表示されたら自動入力を開始します。")
            st.write("※手動で予約ページまで進んでください。")

            # Simple loop to detect common form elements
            found_form = False
            for _ in range(300): # 5 minute timeout
                if await page.query_selector("input"):
                    found_form = True
                    # Small delay to let all fields load
                    await asyncio.sleep(2)
                    break
                await asyncio.sleep(1)

            if found_form:
                await fill_form_best_effort(page, info, reservation_details, custom_selectors_json)
                st.success("自動入力の試行が完了しました。")

            st.warning("注: サイトごとにフォーム構造が異なるため、入力漏れがある場合があります。")
            st.write("ブラウザを開いたままにします。内容を確認し、予約を確定させてください。")

            # Keep browser open
            while True:
                await asyncio.sleep(1)
                if page.is_closed():
                    break

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
        finally:
            st.info("ブラウザを終了するにはアプリを停止してください。")

if st.button("待機開始 / 即時実行（テスト）"):
    now = datetime.datetime.now()

    if scheduled_datetime > now:
        wait_seconds = (scheduled_datetime - now).total_seconds()
        st.warning(f"{wait_seconds:.1f} 秒待機します...")

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(int(wait_seconds)):
            time.sleep(1)
            remaining = int(wait_seconds - i)
            progress = (i + 1) / wait_seconds
            progress_bar.progress(progress)
            status_text.text(f"実行まであと {remaining} 秒...")

            if remaining <= 0:
                break

        st.success("実行時間になりました！")
    else:
        st.info("設定時間が過去または現在のため、即時実行します。")

    if not target_url:
        st.error("URLを指定してください。")
    else:
        reservation_details = {
            "stay_date": stay_date,
            "num_guests": num_guests,
            "companions": companion_names,
            "custom_selectors": custom_selectors
        }
        asyncio.run(run_reservation(target_url, PERSONAL_INFO, reservation_details))

st.divider()
st.caption("※Playwrightがインストールされている必要があります。初回実行前に `playwright install` を実行してください。")
