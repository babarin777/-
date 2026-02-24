@echo off
echo Google起動アプリを開始しています...
python google_launcher.py
if %errorlevel% neq 0 (
    echo.
    echo Pythonがインストールされていないか、パスが通っていない可能性があります。
    echo Pythonをインストールしてから実行してください。
    pause
)
