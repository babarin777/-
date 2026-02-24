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
%PY_CMD% run_app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application failed to start.
    pause
)
endlocal
