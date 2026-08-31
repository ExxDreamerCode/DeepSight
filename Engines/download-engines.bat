@echo off
setlocal enabledelayedexpansion

if not exist "D:\DeepSight\Engines" mkdir "D:\DeepSight\Engines"

echo Downloading Ember...
powershell -Command "$emberZip = Join-Path $env:TEMP 'ember.zip'; $extractPath = Join-Path $env:TEMP 'ember_extract'; $targetDir = 'D:\DeepSight\Engines'; Invoke-WebRequest -Uri 'https://github.com/ExxDreamerCode/Ember/releases/download/V1.3.0/ember-1.3.0-764568b5-windows-amd64.zip' -OutFile $emberZip -UseBasicParsing; New-Item -ItemType Directory -Force -Path $extractPath | Out-Null; Expand-Archive -LiteralPath $emberZip -DestinationPath $extractPath -Force; $exeFile = Get-ChildItem -Path $extractPath -Recurse -Filter 'ember.exe' | Select-Object -First 1; Copy-Item $exeFile.FullName (Join-Path $targetDir 'ember.exe') -Force; Remove-Item $emberZip -Force; Remove-Item $extractPath -Recurse -Force"
if errorlevel 1 (
    echo Failed to download Ember!
    pause
    exit /b 1
)
echo Ember downloaded successfully!

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