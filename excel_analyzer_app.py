import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import openai
import traceback
import io

# ページ設定
st.set_page_config(page_title="Excelデータ解析アプリ", layout="wide")

def sanitize_dataframe(df):
    """
    Streamlit(Apache Arrow)でのシリアライズエラーを避けるため、
    object型などの複雑なデータ型を文字列に変換する。
    """
    for col in df.columns:
        if df[col].dtype == 'object':
            # 文字列に変換する
            df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
    return df

def get_analysis_code(df_info, user_query, api_key):
    """
    OpenAI APIを使用して、データ解析のためのPythonコードを生成する。
    """
    client = openai.OpenAI(api_key=api_key)

    system_prompt = """
あなたはデータサイエンティストです。提供されたデータのスキーマに基づき、ユーザーの要求に応えるためのPythonコードを生成してください。
以下のライブラリが使用可能です: pandas (pd), plotly.express (px), plotly.graph_objects (go), streamlit (st)。

生成するコードは、以下のシグネチャを持つ関数 `analyze_data(df)` の形式にしてください。
```python
def analyze_data(df):
    # ここに解析と可視化のコードを記述
    # 例: st.write("結果"), fig = px.bar(...), st.plotly_chart(fig)
```
注意点:
- グラフは必ず `st.plotly_chart()` を使用して表示してください。
- 解析結果は `st.write()` や `st.table()`, `st.dataframe()` を使用して分かりやすく表示してください。
- 余計な説明は省き、コードブロックのみを返してください。
"""

    user_prompt = f"""
データスキーマ:
{df_info}

ユーザーの要求:
{user_query}
"""

    response = client.chat.completions.create(
        model="gpt-4o", # または "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )

    content = response.choices[0].message.content
    # コードブロックからコードを抽出
    if "```python" in content:
        code = content.split("```python")[1].split("```")[0]
    elif "```" in content:
        code = content.split("```")[1].split("```")[0]
    else:
        code = content

    return code

@st.cache_data
def load_excel(uploaded_file):
    """Excelファイルをキャッシュ付きで読み込む"""
    return pd.ExcelFile(uploaded_file, engine='openpyxl')

@st.cache_data
def parse_sheet(xl, sheet_name):
    """特定のシートをキャッシュ付きでパースする"""
    return xl.parse(sheet_name)

def main():
    st.title("📊 Excelデータ解析アプリ")
    st.markdown("""
    Excelファイルをアップロードし、解析したい内容を自然言語で入力してください。
    AIがデータを解析し、グラフや表を作成します。
    """)

    # サイドバーで設定
    with st.sidebar:
        st.header("設定")
        api_key = st.text_input("OpenAI API Key", type="password")
        if not api_key:
            st.warning("APIキーを入力してください。")

    # ファイルアップローダー
    uploaded_file = st.file_uploader("Excelファイルを選択してください", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            # Excelファイルの読み込み
            xl = load_excel(uploaded_file)
            sheet_names = xl.sheet_names

            # シート選択
            selected_sheet = st.selectbox("解析対象のシートを選択してください", sheet_names)
            df = parse_sheet(xl, selected_sheet)

            # データプレビュー
            st.subheader("データプレビュー")
            st.dataframe(df.head())

            # 解析リクエスト入力
            st.subheader("解析内容の入力")
            user_query = st.text_area("どのような解析を行いたいですか？",
                                     placeholder="例: 売上の推移を折れ線グラフで表示して。カテゴリ別の合計も表で出して。")

            if st.button("解析実行"):
                if not api_key:
                    st.error("APIキーを設定してください。")
                elif not user_query:
                    st.error("解析内容を入力してください。")
                else:
                    with st.spinner("AIが解析中..."):
                        # データ情報の作成
                        buffer = io.StringIO()
                        df.info(buf=buffer)
                        df_info = buffer.getvalue()

                        # AIにコードを生成させる
                        try:
                            code = get_analysis_code(df_info, user_query, api_key)

                            st.subheader("解析結果")

                            # 生成されたコードを実行
                            # 安全のため、特定のローカル変数のみを渡す
                            local_vars = {
                                'pd': pd,
                                'px': px,
                                'go': go,
                                'st': st,
                                'df': sanitize_dataframe(df)
                            }

                            exec(code, globals(), local_vars)

                            if 'analyze_data' in local_vars:
                                local_vars['analyze_data'](local_vars['df'])
                            else:
                                st.error("解析関数の生成に失敗しました。")
                                st.code(code)

                        except Exception as e:
                            st.error(f"エラーが発生しました: {e}")
                            st.expander("詳細なエラーログ").code(traceback.format_exc())
                            if 'code' in locals():
                                st.expander("生成されたコード").code(code)

        except Exception as e:
            st.error(f"ファイルの読み込みに失敗しました: {e}")

if __name__ == "__main__":
    main()
