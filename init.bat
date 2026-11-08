@echo off
setlocal enabledelayedexpansion
title Skyper - First Time Setup

echo ============================================
echo   Skyper RAG Platform - First Time Setup
echo ============================================
echo.

cd /d "%~dp0"

echo [1/6] Checking prerequisites...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Docker not found. Please install Docker Desktop.
    pause
    exit /b 1
)
echo   [OK] Docker

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Node.js not found.
    pause
    exit /b 1
)
echo   [OK] Node.js

where conda >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Conda not found.
    pause
    exit /b 1
)
echo   [OK] Conda

echo.
echo [2/6] Creating Conda environment 'skyper' (Python 3.12)...
call conda create -n skyper python=3.12 -y
if %errorlevel% neq 0 (
    echo [FAIL] Failed to create conda environment.
    pause
    exit /b 1
)

echo.
echo [3/6] Installing Python dependencies...
call conda run -n skyper pip install -r "%~dp0Skyper-python\requirements.txt"
if %errorlevel% neq 0 (
    echo [FAIL] pip install failed.
    pause
    exit /b 1
)

echo.
echo [4/6] Setting up .env...
if not exist "%~dp0Skyper-python\.env" (
    copy "%~dp0Skyper-python\.env.example" "%~dp0Skyper-python\.env" >nul
    echo   Created .env from .env.example
    echo   [WARN] Please edit Skyper-python\.env and configure your API keys!
) else (
    echo   .env already exists, skipping.
)

echo.
echo [5/6] Initializing database...
docker compose -f "%~dp0docker-compose.yml" up -d
echo   Waiting for PostgreSQL to be ready...
timeout /t 8 /nobreak >nul
call conda run -n skyper python "%~dp0Skyper-python\init_db.py"
if %errorlevel% neq 0 (
    echo [WARN] DB init may have issues. Make sure Docker Desktop is running.
)

echo.
echo [6/6] Installing frontend dependencies...
cd /d "%~dp0Skyper-frontend"
call npm install
if %errorlevel% neq 0 (
    echo [FAIL] npm install failed.
    cd /d "%~dp0"
    pause
    exit /b 1
)

cd /d "%~dp0"
echo.
echo ============================================
echo   Setup Complete!
echo   Next: run start.bat to launch the platform
echo ============================================
pause
