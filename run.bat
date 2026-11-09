@echo off
title ClashBoard Launcher
echo ========================================================
echo Starting ClashBoard - Timetable Clash Resolver
echo ========================================================
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
