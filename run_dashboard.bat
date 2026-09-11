@echo off
title GSC Pro Dashboard Launcher
cd /d "%~dp0"
echo ========================================================
echo        Starting GSC Pro Dashboard (Streamlit)...
echo ========================================================
echo.
echo URL: http://localhost:8501
echo.
python -m streamlit run app_ui.py
pause
