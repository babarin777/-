import streamlit as st
import pandas as pd
import plotly.express as px
import openai
import io
import sys

print("--- excel_analyzer_app.py is loading... ---")

# Set page config - must be the first streamlit command
try:
    st.set_page_config(page_title="Excel Analysis App", layout="wide")
except Exception as e:
    # If this fails, something is fundamentally wrong with streamlit
    print(f"Critical Streamlit Error: {e}")
    sys.exit(1)

def sanitize_dataframe(df):
    """
    Streamlitのst.dataframeでArrowエラーが出るのを防ぐため、
    データのクリーニングと型変換を行います。
    """
    try:
        df_clean = df.copy()

        # 1. 混合型や特殊なオブジェクト型を文字列に変換
        for col in df_clean.columns:
            # カラム全体の型を確認
            if df_clean[col].dtype == 'object':
                # 各要素が実際にどのような型かを確認し、必要に応じて変換
                df_clean[col] = df_clean[col].apply(lambda x:
                    str(x) if x is not None and not (isinstance(x, float) and pd.isna(x)) else x
                )

            # 2. カテゴリ型はArrowでエラーになりやすいため文字列にする
            if str(df_clean[col].dtype) == 'category':
                df_clean[col] = df_clean[col].astype(str)

        # 3. インデックスのリセット（特殊なインデックスによるエラー回避）
        # df_clean = df_clean.reset_index(drop=True)

        return df_clean
    except Exception as e:
        st.error(f"データ変換中にエラーが発生しました: {e}")
        return df

st.title("📊 Excel 解析アプリ")
st.markdown("""
このアプリでは、Excelファイルをアップロードして、自由な内容で解析を行うことができます。
OpenAIのAPIキーを設定すると、自然言語での高度な解析が可能になります。
""")

# Sidebar for configuration
st.sidebar.header("設定")
api_key = st.sidebar.text_input("OpenAI API Key", type="password")

# Initialize OpenAI client if API key is provided
client = None
if api_key:
    try:
        client = openai.OpenAI(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"OpenAIクライアントの初期化に失敗しました: {e}")

# File uploader
uploaded_file = st.sidebar.file_uploader("Excelファイルをアップロード", type=["xlsx", "xls"])

if uploaded_file:
    # Load Excel to get sheet names
    try:
        # Reset file pointer just in case
        uploaded_file.seek(0)

        xl = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet_names = xl.sheet_names
        selected_sheet = st.sidebar.selectbox("解析するシートを選択", sheet_names)

        # Load selected sheet - Use the xl object to avoid pointer issues
        df = xl.parse(selected_sheet)

        st.subheader(f"シート: {selected_sheet} のデータプレビュー")
        try:
            st.dataframe(sanitize_dataframe(df.head(10)))
        except Exception as e:
            st.warning("データの表示中にエラーが発生しました。代替方式で表示します。")
            st.table(df.head(10))

        # Basic Info
        with st.expander("データの基本情報"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**カラム一覧:**")
                st.write(df.columns.tolist())
            with col2:
                st.write("**データ型:**")
                st.write(df.dtypes)
            st.write(f"**合計行数:** {len(df)}")
            st.write(f"**欠損値数:**")
            st.write(df.isnull().sum())

        # Analysis section
        st.divider()
        st.subheader("🔍 解析の実行")
        analysis_prompt = st.text_area("解析して欲しい内容を入力してください", placeholder="例: 各項目の統計量を出して / カテゴリごとの売上合計を棒グラフにして / 日付ごとの推移を折れ線グラフで見せて")

        if st.button("解析実行"):
            if not analysis_prompt:
                st.warning("解析内容を入力してください。")
            elif not api_key:
                st.info("APIキーが入力されていないため、基本的な統計情報を表示します。高度な解析にはAPIキーが必要です。")
                st.write("**基本統計量:**")
                st.write(df.describe(include='all'))
            else:
                with st.spinner("AIが解析中..."):
                    try:
                        # Prepare context for AI
                        buffer = io.StringIO()
                        df.info(buf=buffer)
                        df_info = buffer.getvalue()
                        sample_data = df.head(5).to_string()

                        system_prompt = """
                        あなたは優秀なデータサイエンティストです。ユーザーの要望に合わせて、提供されたPandas DataFrame 'df' を解析し、Pythonコードを生成してください。

                        制約事項:
                        1. 出力は実行可能なPythonコードのみを含めてください（マークダウンのコードブロックは使わないでください）。
                        2. グラフを表示する場合は Plotly Express (px) を使用してください。
                        3. 作成したグラフ（plotlyのfigureオブジェクト）は必ず 'fig' という変数名に代入してください。
                        4. 計算結果や表を表示したい場合は、'result_text' という変数に文字列を代入するか、'result_df' という変数にDataFrameを代入してください。
                        5. ライブラリは 'import pandas as pd', 'import plotly.express as px' が既に読み込まれていると仮定して良いです。
                        6. データの加工が必要な場合は、元の 'df' を変更せずコピーを作成して使用してください。
                        """

                        user_message = f"""
                        データフレームの情報:
                        {df_info}

                        サンプルデータ:
                        {sample_data}

                        ユーザーの要望:
                        {analysis_prompt}
                        """

                        # Use new OpenAI API (v1+)
                        response = client.chat.completions.create(
                            model="gpt-4o", # Or gpt-3.5-turbo
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_message}
                            ],
                            temperature=0
                        )

                        code = response.choices[0].message.content.strip()
                        # Remove markdown code blocks if any
                        if code.startswith("```python"):
                            code = code[9:-3]
                        elif code.startswith("```"):
                            code = code[3:-3]

                        # st.code(code, language='python') # For debugging

                        # Prepare execution environment
                        local_vars = {'df': df, 'pd': pd, 'px': px}
                        exec(code, globals(), local_vars)

                        # Show results
                        if 'result_text' in local_vars:
                            st.write("**解析結果:**")
                            st.write(local_vars['result_text'])

                        if 'result_df' in local_vars:
                            st.write("**解析データ表:**")
                            try:
                                st.dataframe(sanitize_dataframe(local_vars['result_df']))
                            except Exception:
                                st.table(local_vars['result_df'])

                        if 'fig' in local_vars:
                            st.write("**可視化結果:**")
                            st.plotly_chart(local_vars['fig'], use_container_width=True)

                        if not any(k in local_vars for k in ['result_text', 'result_df', 'fig']):
                            st.info("解析は完了しましたが、表示する結果（fig, result_text, result_df）が定義されませんでした。")

                    except Exception as e:
                        st.error(f"解析中にエラーが発生しました: {e}")
                        st.write("生成されたコード:")
                        st.code(code if 'code' in locals() else "N/A")

    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました: {e}")

else:
    st.info("左側のサイドバーからExcelファイルをアップロードしてください。")

    # Simple Example for demonstration if no file is uploaded
    if st.checkbox("サンプルデータを表示"):
        sample_df = pd.DataFrame({
            "日付": pd.date_range(start="2023-01-01", periods=10, freq="D"),
            "売上": [100, 150, 200, 180, 250, 300, 280, 350, 400, 380],
            "カテゴリ": ["A", "B", "A", "C", "B", "A", "C", "A", "B", "C"]
        })
        st.write("サンプルデータ:")
        st.dataframe(sample_df)

        fig = px.line(sample_df, x="日付", y="売上", color="カテゴリ", title="サンプル売上推移")
        st.plotly_chart(fig)
