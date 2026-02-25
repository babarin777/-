import streamlit as st
import pandas as pd
from openai import OpenAI

# ページ設定
st.set_page_config(page_title="Excel Q&A App", layout="wide")

st.title("Excel Q&A アプリ")
st.write("Excelファイルをアップロードして、その内容についてAIに質問できるアプリです。")

# サイドバーでAPIキーとモデルの設定
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("OpenAI API Key", type="password", help="OpenAIのAPIキーを入力してください。")
    model = st.selectbox("モデルを選択", ["gpt-4o", "gpt-4o-mini"], index=0)
    st.info("※APIキーは保存されません。ブラウザを更新すると再入力が必要です。")

# ①入力するシート（ファイルアップローダー）
st.subheader("① Excelシートの入力")
uploaded_file = st.file_uploader("Excelファイルをアップロードしてください", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        # Excelファイルの全シート名を読み込む
        xl = pd.ExcelFile(uploaded_file)
        sheet_names = xl.sheet_names

        # シート選択
        if len(sheet_names) > 1:
            selected_sheet = st.selectbox("分析するシートを選択してください", sheet_names)
        else:
            selected_sheet = sheet_names[0]
            st.write(f"シート「{selected_sheet}」を読み込みました。")

        # 選択されたシートをデータフレームとして読み込む
        df = xl.parse(selected_sheet)

        # データプレビューの表示
        with st.expander("データのプレビューを表示"):
            st.dataframe(df)

        # ②質問内容
        st.subheader("② 質問内容")
        question = st.text_area("データについて聞きたいことを入力してください",
                                placeholder="例：このデータの概要を教えてください。\n最も数値が高い項目は何ですか？",
                                height=150)

        # 実行ボタン
        if st.button("AIに質問する", type="primary"):
            if not api_key:
                st.error("サイドバーでOpenAI APIキーを入力してください。")
            elif not question:
                st.warning("質問内容を入力してください。")
            else:
                with st.spinner("AIがデータを解析して回答を生成しています..."):
                    try:
                        # OpenAIクライアントの初期化
                        client = OpenAI(api_key=api_key)

                        # データフレームをテキスト（CSV形式）に変換してプロンプトに含める
                        # 行数が多い場合は先頭と末尾のみを送るなどの工夫が必要だが、一旦全て送る（大規模データは別途考慮）
                        csv_data = df.to_csv(index=False)

                        # プロンプトの構築
                        prompt = f"""
以下のExcelデータの内容に基づいて、ユーザーの質問に日本語で答えてください。

### 対象シート名:
{selected_sheet}

### データ (CSV形式):
{csv_data}

### ユーザーの質問:
{question}
"""

                        # API呼び出し
                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": "あなたは優秀なデータアナリストです。提供されたデータの内容を正確に把握し、ユーザーの質問に対して分かりやすく回答してください。"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0
                        )

                        # 回答の表示
                        answer = response.choices[0].message.content
                        st.subheader("AIの回答")
                        st.markdown(answer)

                    except Exception as e:
                        st.error(f"エラーが発生しました: {str(e)}")

    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")
else:
    st.info("Excelファイルをアップロードしてください。")

# フッター
st.divider()
st.caption("© 2024 Excel Q&A Assistant")

# 直接実行された場合のランチャー
if __name__ == "__main__":
    import sys
    from streamlit.web import cli as stcli

    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]] + sys.argv[1:]
        sys.exit(stcli.main())
