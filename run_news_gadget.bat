@echo off
echo ニュースガジェットを起動しています...
python news_gadget.py
if %errorlevel% neq 0 (
    echo.
    echo エラーが発生しました。
    echo 1. Pythonがインストールされているか確認してください。
    echo 2. 必要ライブラリをインストールしてください: pip install requests feedparser
    pause
)
