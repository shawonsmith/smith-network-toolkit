@echo off
title Smith IT Company Network Diagnostic Toolkit
cd /d "%~dp0"

echo =========================================================
echo   Starting Smith IT Company Network Diagnostic Toolkit
echo =========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in your PATH!
    echo Please install Python 3.8+ from https://www.python.org/
    echo or check your Environment Variables.
    echo.
    pause
    exit /b 1
)

python run.py
if errorlevel 1 (
    echo.
    echo Tool exited with an error.
    pause
)
