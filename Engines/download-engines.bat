@echo off
setlocal

REM Convenience wrapper for Windows: the real downloader is Engines/fetch_engines.py, which reads
REM the pins in engines.json and verifies every hash. It is shared with CI so that a local build
REM and a release can never fetch different binaries.
REM Ember is MIT, Stockfish is GPL-3.0 (licenses/GPL-3.0.txt).

set SCRIPT=%~dp0fetch-engines.py

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 "%SCRIPT%" %*
    goto done
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python "%SCRIPT%" %*
    goto done
)

echo Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again.
exit /b 1

:done
if errorlevel 1 (
    echo.
    echo Failed to download the engines.
)

echo.
pause
