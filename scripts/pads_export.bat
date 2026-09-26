@echo off
REM ============================================================
REM PADS Layout - Automated Export Batch File
REM ============================================================
REM Purpose: Launch PADS Layout, open a PCB file, and run the
REM          export script to generate all files needed for
REM          EE Review skill processing.
REM
REM Usage:
REM   pads_export.bat "C:\path\to\your_board.pcb"
REM
REM Prerequisites:
REM   - PADS Layout installed (VX.2.2 or later)
REM   - pads_export_all.bas in the same directory as this file
REM   - Run on the machine/VM where PADS is installed
REM ============================================================

setlocal

REM --- Check arguments ---
if "%~1"=="" (
    echo Usage: pads_export.bat "C:\path\to\board.pcb"
    echo.
    echo Example: pads_export.bat "D:\Projects\MyBoard\board.pcb"
    pause
    exit /b 1
)

set "PCB_FILE=%~1"
set "SCRIPT_DIR=%~dp0"

REM --- Try to find PADS Layout executable ---
REM Adjust these paths based on your PADS installation
set "PADS_PATHS=C:\MentorGraphics\PADSVX.2.2\SDD_HOME\Programs\layout.exe;C:\MentorGraphics\PADSVX.2.7\SDD_HOME\Programs\layout.exe;C:\MentorGraphics\PADSVX.2.8\SDD_HOME\Programs\layout.exe;C:\PADS\SDD_HOME\Programs\layout.exe"

set "PADS_EXE="
for %%P in (%PADS_PATHS%) do (
    if exist "%%P" (
        set "PADS_EXE=%%P"
        goto found_pads
    )
)

REM --- Ask user for PADS path if not found ---
echo PADS Layout executable not found in common locations.
echo Please enter the full path to layout.exe:
set /p PADS_EXE="layout.exe path: "

if not exist "%PADS_EXE%" (
    echo ERROR: layout.exe not found at: %PADS_EXE%
    pause
    exit /b 1
)

:found_pads
echo ============================================================
echo  PADS Automated Export for EE Review
echo ============================================================
echo  PADS Layout:  %PADS_EXE%
echo  PCB File:     %PCB_FILE%
echo  Script:       %SCRIPT_DIR%pads_export_all.bas
echo ============================================================
echo.

REM --- Launch PADS with the script ---
echo Launching PADS Layout...
"%PADS_EXE%" "%PCB_FILE%" /runscript "%SCRIPT_DIR%pads_export_all.bas"

echo.
echo PADS has closed. Check the output directory for exported files.
echo The files are typically in the same folder as your PCB file,
echo under a subfolder named "EE_Review_Export".
echo.
echo Next steps:
echo   1. Copy the EE_Review_Export folder to your host machine
echo   2. Run: python3 convert_layout.py board.asc --export-all
echo.
pause
