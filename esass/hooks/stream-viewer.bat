@echo off
title ESASS Live Event Stream
cd /d "%~dp0"
python stream-viewer.py %*
pause
