@echo off
echo Excel Analysis App を起動しています...
python run_app.py
if %errorlevel% neq 0 (
    echo.
    echo エラーが発生しました。上記を確認してください。
    pause
)
