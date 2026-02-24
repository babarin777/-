@echo off
setlocal
cd /d "%~dp0"

echo --- Excel Data Analyzer Launcher ---
echo Checking Python installation...

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PY_CMD=py
    ) else (
        python3 --version >nul 2>&1
        if %errorlevel% equ 0 (
            set PY_CMD=python3
        ) else (
            echo [ERROR] Python is not installed or not in PATH.
            pause
            exit /b 1
        )
    )
)

echo Using: %PY_CMD%
echo.
echo [INFO] ブラウザで「接続が拒否されました」と出る場合は、
echo        表示される別のURL(127.0.0.1やIPアドレス)を試してください。
echo.

%PY_CMD% run_app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application failed to start.
    echo.
    echo [TIP] ZIPファイルを展開(解凍)せずに実行していませんか？
    echo       右クリックから「すべて展開」を選択した後に実行してください。
    echo.
    echo 詳細は README.txt を確認してください。
    pause
)
endlocal
