@echo off
title ESASS Unified Dashboard
cd /d "%~dp0"
mode con: cols=110 lines=55
python esass_dashboard.py
pause
