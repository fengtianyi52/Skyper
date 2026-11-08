@echo off
setlocal
title Skyper Agent Workspace
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0skyper.ps1" -Action Start %*
set "SKYPER_EXIT=%ERRORLEVEL%"
if not "%SKYPER_EXIT%"=="0" pause
exit /b %SKYPER_EXIT%
