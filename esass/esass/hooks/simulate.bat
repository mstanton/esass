@echo off
title ESASS Event Simulator
cd /d "%~dp0"
python simulate_events.py --speed 2
pause
