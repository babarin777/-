@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo   Excel Analysis App 起動ランチャー
echo ==================================================

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
    echo Python をインストールし、PATH に追加してください。
    echo https://www.python.org/
    pause
    exit /b 1
)

echo 使用する Python: %PYTHON_CMD%
"%PYTHON_CMD%" run_app.py

if %errorlevel% neq 0 (
    echo.
    echo [エラー] アプリの起動中に問題が発生しました。
    pause
)
