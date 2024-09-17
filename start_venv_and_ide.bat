@echo off
setlocal

REM Define environment variables
set "VENV_PATH=%USERPROFILE%\Envs\FUS_DS_PACKAGE"
set IDE=spyder

REM Activate the virtual environment and launch the IDE
call "%VENV_PATH%\Scripts\activate
start %IDE%

endlocal