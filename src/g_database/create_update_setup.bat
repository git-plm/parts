@echo off
setlocal enabledelayedexpansion

:: Define all of your libs here
set "GPLMLIBS=ana cap cnn cpd dio ics ind mpu mcu pwr rfm res reg xtr osc opt art swi"

:: Loop through each library
for %%L in (%GPLMLIBS%) do (
    echo Processing library: %%L

    :: Drop the existing table (if it exists)
    sqlite3 parts.sqlite "DROP TABLE IF EXISTS %%L"

    :: Import the corresponding CSV file into the table
    sqlite3 -csv parts.sqlite ".import %%L.csv %%L"

    if errorlevel 1 (
        echo Error processing library: %%L
		:: Prevent the window from closing immediately
		pause
        exit /b 1
    )
)

echo Database creation completed successfully.

:: Prevent the window from closing immediately
pause
