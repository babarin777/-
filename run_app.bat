@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo   Excel Analysis App 起動ランチャー (デバッグ版)
echo ==================================================

:: Check if Python is available
set PYTHON_CMD=
for %%i in (python.exe python3.exe py.exe) do (
    where %%i >nul 2>nul
    if !errorlevel! equ 0 (
        set PYTHON_CMD=%%i
        goto :found
    )
)

:found
if "%PYTHON_CMD%"=="" (
    echo [エラー] Python が見つかりませんでした。
    echo 以下のいずれかを確認してください：
    echo 1. Python がインストールされているか
    echo 2. インストール時に "Add Python to PATH" にチェックを入れたか
    echo.
    echo ダウンロード先: https://www.python.org/
    pause
    exit /b 1
)

echo [情報] 使用する Python: %PYTHON_CMD%

:: Run the diagnostic script
"%PYTHON_CMD%" run_app.py

if %errorlevel% neq 0 (
    echo.
    echo [エラー] アプリが終了しました (終了コード: %errorlevel%)
    echo 詳細は startup_debug.log を確認してください。
    pause
) else (
    echo.
    echo [情報] アプリケーションを終了しました。
    pause
)
