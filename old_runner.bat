@echo off
setlocal

set PROJECT_DIR=C:\Users\GBSAmericas.Bot\PycharmProjects\ExpertB-Extraction
set VENV_SCRIPTS=%PROJECT_DIR%\.venv\Scripts
set LOGFILE=%PROJECT_DIR%\runner_log.txt

echo ==================================================== >> "%LOGFILE%"
echo Run started: %date% %time% >> "%LOGFILE%"

REM Check venv exists before touching PATH
if not exist "%VENV_SCRIPTS%\python.exe" (
    echo [ERROR] Virtual environment not found at %VENV_SCRIPTS% >> "%LOGFILE%"
    echo Virtual environment not found at %VENV_SCRIPTS%
    pause
    exit /b 1
)

REM Put venv Scripts folder first on PATH instead of calling activate.bat
REM (avoids activate.bat's internal "exit" potentially killing this whole process)
set PATH=%VENV_SCRIPTS%;%PATH%

cd /d "%PROJECT_DIR%"

REM Verify Azure CLI auth before running the script
az account show >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Not logged into Azure CLI. Attempting login... >> "%LOGFILE%"
    az login
)

python main.py >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    echo [ERROR] main.py exited with an error. See log for details. >> "%LOGFILE%"
    echo main.py failed. Check runner_log.txt for details.
    pause
) else (
    echo Run completed successfully: %date% %time% >> "%LOGFILE%"
)

endlocal


@echo offcmd /k "cd /d C:\Users\GBSAmericas.Bot\PycharmProjects\ExpertB-Extraction\.venv\Scripts & activate & cd /d C:\Users\GBSAmericas.Bot\PycharmProjects\ExpertB-Extraction & python main.py"