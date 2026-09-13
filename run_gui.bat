@echo off
title Smith IT Company Network Diagnostic Toolkit (GUI)
cd /d "%~dp0"

echo Starting Desktop GUI...
python -m src.gui.app
if errorlevel 1 (
    echo.
    echo GUI exited with an error.
    pause
)
