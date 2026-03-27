import streamlit as st
import sys

print("--- test_streamlit.py is loading... ---")

st.title("Streamlit 起動テスト")
st.write("この画面が表示されていれば、Streamlit 自体は正しく動作しています。")
st.write(f"Python バージョン: {sys.version}")

if st.button("クリックして動作確認"):
    st.balloons()
    st.success("ボタンがクリックされました！")
