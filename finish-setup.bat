@echo off
setlocal
title Finish Skyper setup after Windows restart
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0finish-setup.ps1"
set "SKYPER_EXIT=%ERRORLEVEL%"
pause
exit /b %SKYPER_EXIT%
