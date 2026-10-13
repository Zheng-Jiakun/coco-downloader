@echo off
REM Compile Qt Resource Files for Desktop Application
echo Compiling Qt resources...

cd /d "%~dp0"
python -m PyQt5.pyrcc_main app/resource/resource.qrc -o app/common/resource.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Resources compiled successfully!
    echo Output: app/common/resource.py
) else (
    echo.
    echo [ERROR] Resource compilation failed!
)

echo.
pause
