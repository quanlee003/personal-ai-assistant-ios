@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Chua co moi truong Python. Xem README de cai dat.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m iphone_assistant.desktop
