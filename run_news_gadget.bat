@echo off
setlocal
cd /d %~dp0
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "news_gadget.ps1"
if %errorlevel% neq 0 (
    echo エラーが発生しました。PowerShellの設定を確認してください。
    pause
)
