@echo off
setlocal
cd /d "%~dp0\.."
echo ========================================================
echo  Running Avascry 5-Site MongoDB Backup Pipeline
echo ========================================================
python scripts\backup_databases.py --avascry %*
if %ERRORLEVEL% equ 0 (
    echo [OK] Backup completed successfully.
) else (
    echo [ERROR] Backup failed with exit code %ERRORLEVEL%.
)
