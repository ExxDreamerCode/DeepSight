@echo off
setlocal enabledelayedexpansion

REM The engine versions are pinned here: bumping Ember means bumping BUILTIN_ENGINE_VERSIONS in
REM deepsight/engine_registry.py, the file names in both READMEs and THIRD_PARTY_NOTICES.md too.
REM Ember is MIT, Stockfish is GPL-3.0 (licenses/GPL-3.0.txt).
set EMBER_VERSION=1.3.1
set EMBER_REV=9e015493

if not exist "D:\DeepSight\Engines" mkdir "D:\DeepSight\Engines"

echo Downloading Ember %EMBER_VERSION%...
powershell -Command "$emberZip = Join-Path $env:TEMP 'ember.zip'; $extractPath = Join-Path $env:TEMP 'ember_extract'; $targetDir = 'D:\DeepSight\Engines'; Invoke-WebRequest -Uri 'https://github.com/ExxDreamerCode/Ember/releases/download/V%EMBER_VERSION%/ember-%EMBER_VERSION%-%EMBER_REV%-windows-amd64.zip' -OutFile $emberZip -UseBasicParsing; New-Item -ItemType Directory -Force -Path $extractPath | Out-Null; Expand-Archive -LiteralPath $emberZip -DestinationPath $extractPath -Force; $exeFile = Get-ChildItem -Path $extractPath -Recurse -Filter 'ember.exe' | Select-Object -First 1; Copy-Item $exeFile.FullName (Join-Path $targetDir 'ember-%EMBER_VERSION%.exe') -Force; Remove-Item $emberZip -Force; Remove-Item $extractPath -Recurse -Force"
if errorlevel 1 (
    echo Failed to download Ember!
    pause
    exit /b 1
)
echo Ember %EMBER_VERSION% downloaded successfully!

echo.
echo Downloading Stockfish...
powershell -Command "$stockfishZip = Join-Path $env:TEMP 'stockfish.zip'; $targetDir = 'D:\DeepSight\Engines'; Invoke-WebRequest -Uri 'https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64.zip' -OutFile $stockfishZip -UseBasicParsing; Expand-Archive -LiteralPath $stockfishZip -DestinationPath $env:TEMP -Force; Copy-Item (Join-Path $env:TEMP 'stockfish\stockfish-windows-x86-64.exe') (Join-Path $targetDir 'stockfish-windows-x86-64.exe') -Force; Remove-Item $stockfishZip -Force; Remove-Item (Join-Path $env:TEMP 'stockfish') -Recurse -Force"
if errorlevel 1 (
    echo Failed to download Stockfish!
    pause
    exit /b 1
)
echo Stockfish downloaded successfully!

echo.
echo All engines downloaded to D:\DeepSight\Engines!
echo.
echo Files in D:\DeepSight\Engines:
dir "D:\DeepSight\Engines\*.exe"
echo.
pause