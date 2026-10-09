@echo off
title vietBook Runner
echo Starting vietBook...
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    streamlit run app.py
) else (
    python -m streamlit run app.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] An error occurred while launching vietBook.
    pause
)
