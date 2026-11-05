@echo off

:: Install one Python version from 3.10 to 3.14, 3.11 or higher recommended, from
:: https://www.python.org/downloads/. Only the one you use is needed, not all of them.

:: Set the path of the python.exe to use. It must be Python 3.10 to 3.14. The default is where
:: the python.org installer puts Python 3.11 when you choose Install Now (for the current user).
set "DEFAULT_PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

:: Set a default virtual environment name
set "DEFAULT_VENV_NAME=FUS_DS_PACKAGE"

:: Set a default virtual environment directory
set "DEFAULT_VENV_DIR=%USERPROFILE%\Envs"

:: Collect input parameters with fallbacks to defaults
set "PYTHON_PATH=%~1"
if "%PYTHON_PATH%"=="" set "PYTHON_PATH=%DEFAULT_PYTHON_PATH%"

set "VENV_NAME=%~2"
if "%VENV_NAME%"=="" set "VENV_NAME=%DEFAULT_VENV_NAME%"

set "VENV_DIR=%~3"
if "%VENV_DIR%"=="" set "VENV_DIR=%DEFAULT_VENV_DIR%"

:: Check if the Envs directory exists; if not, create it
if not exist "%VENV_DIR%" (
    mkdir "%VENV_DIR%"
    echo Created directory "%VENV_DIR%"
)

:: Check that the python.exe at the specified path is one of 3.10 to 3.14
for /f "delims=" %%a in ('"%PYTHON_PATH%" --version 2^>nul') do set "PYTHON_VERSION=%%a"

:: Extract the major and minor version numbers
for /f "tokens=2 delims= " %%b in ("%PYTHON_VERSION%") do set "PYTHON_VERSION=%%b"
echo %PYTHON_VERSION% | findstr /r "^3\.1[0-4]\." >nul
if errorlevel 1 (
    echo The Python at the specified path is not one of 3.10 to 3.14, or it was not found. Give the path of a python.exe of one of these versions, for example: create_venv.bat "C:\Path\To\Python311\python.exe"
    exit /b 1
)

:: Ensure that virtualenv is installed
"%PYTHON_PATH%" -m pip show virtualenv >nul 2>&1
if errorlevel 1 (
    echo Installing virtualenv package...
    "%PYTHON_PATH%" -m pip install virtualenv
) else (
    echo virtualenv is already installed.
)

set "VENV_PATH=%VENV_DIR%\%VENV_NAME%"

:: Check if the virtual environment already exists
if exist "%VENV_PATH%\Scripts\activate" (
    echo Virtual environment already exists at "%VENV_PATH%".
) else (
    echo Creating virtual environment at "%VENV_PATH%".
    "%PYTHON_PATH%" -m virtualenv "%VENV_PATH%"
)

:: Activate the virtual environment
call "%VENV_PATH%\Scripts\activate"

:: Install project-specific dependencies
echo Installing requirements from requirements.txt...
pip install -r requirements.txt

:: Optionally install the GUI: opt-in, since PySide6 is a large download most script users don't need.
:: The 4th parameter (y/n) answers the question up front; without it, ask. A non-interactive run
:: without the parameter skips the GUI.
set "INSTALL_GUI=%~4"
if "%INSTALL_GUI%"=="" set /p "INSTALL_GUI=Also install the GUI (fus_ds_gui)? [y/n]:"
if /i "%INSTALL_GUI%"=="y" (
    echo Installing the GUI...
    pip install ./fus_ds_gui
)

:: Upgrade pip in virtual environment
python.exe -m pip install --upgrade pip

echo Setup complete. To activate the virtual environment, run: call "%VENV_PATH%\Scripts\activate"
echo The virtual environment is located at: "%VENV_PATH%"