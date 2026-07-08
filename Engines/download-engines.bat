@echo off
setlocal enabledelayedexpansion

echo Downloading Ember...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/ExxDreamerCode/Ember/releases/download/V1.1.2/ember.exe' -OutFile 'ember.exe' -UseBasicParsing"
if errorlevel 1 (
    echo Failed to download Ember!
    pause
    exit /b 1
)
echo Ember downloaded successfully!

echo.
echo Downloading Stockfish...
powershell -Command "$stockfishZip = Join-Path $env:TEMP 'stockfish.zip'; Invoke-WebRequest -Uri 'https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64.zip' -OutFile $stockfishZip -UseBasicParsing; Expand-Archive -LiteralPath $stockfishZip -DestinationPath $env:TEMP -Force; Copy-Item (Join-Path $env:TEMP 'stockfish\stockfish-windows-x86-64.exe') 'stockfish-windows-x86-64.exe' -Force; Remove-Item $stockfishZip -Force; Remove-Item (Join-Path $env:TEMP 'stockfish') -Recurse -Force"
if errorlevel 1 (
    echo Failed to download Stockfish!
    pause
    exit /b 1
)
echo Stockfish downloaded successfully!

echo.
echo All engines downloaded!
echo.
echo Files in current directory:
dir *.exe
echo.
pause