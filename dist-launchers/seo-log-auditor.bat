@echo off
REM seo-log-auditor launcher (Windows)
REM
REM Double-click this file. It will:
REM   1. Install `uv` (~30 MB, one-time) if you don't already have it.
REM   2. Run `uvx seo-log-auditor`, which downloads and launches the app.
REM   3. Open http://localhost:8501 in your browser.
REM
REM The console window stays open so you can close the app cleanly with
REM Ctrl-C. To uninstall later: `uv tool uninstall seo-log-auditor`.

setlocal

echo ==^> seo-log-auditor launcher
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo ==^> 'uv' not found. Installing it now ^(one-time, no admin needed^).
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    REM Refresh PATH for this session so uv is found below.
    set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"

    where uv >nul 2>nul
    if errorlevel 1 (
        echo.
        echo ERROR: uv was installed but isn't on PATH.
        echo Close this window, open a new one, and run this launcher again.
        pause
        exit /b 1
    )
)

echo ==^> Launching seo-log-auditor ^(this may take a minute on first run^)...
echo     A browser tab will open at http://localhost:8501.
echo     Press Ctrl-C in this window to stop the app.
echo.

uvx seo-log-auditor

echo.
echo App stopped.
pause
