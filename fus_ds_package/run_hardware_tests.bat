:: Runs the hardware tests for IGT and Sonic Concepts. Edit the settings below, then double-click
:: this file, or run it from a Command Prompt. Extra arguments go to pytest, for example:
::   run_hardware_tests.bat -k abort
::
:: SAFETY: only with a dummy load wired to the driving system, never a real transducer.
:: See "Hardware tests" in docs/python-usage.md and the top of
:: fus_driving_systems/tests/hardware/conftest.py for what every setting does.
@echo off
setlocal

:: ---- Settings: leave a value empty to use its default ------------------------------------

:: Which equipment is connected: igt or sc. Only one can be connected at a time, so each run
:: tests one of them.
set TESTS=igt

:: The virtual environment to use. Leave empty if it is already activated.
set VENV_DIR=

:: IGT. The default needs the "IGT 256 ch. - 1 x 10 ch. (TEST)" setup to be active in
:: ds_config.ini, with IS_PCD15287_01001 as the pretend transducer.
set FDS_HW_DRIVING_SYSTEM=
set FDS_HW_TRANSDUCER=

:: Sonic Concepts. Both are needed to run its tests: the driving system (for example 105-010) and
:: the transducer that is currently selected on the TPO.
set FDS_HW_SC_DRIVING_SYSTEM=
set FDS_HW_SC_TRANSDUCER=

:: ------------------------------------------------------------------------------------------

set FDS_HARDWARE_TESTS=1
if not "%VENV_DIR%"=="" call "%VENV_DIR%\Scripts\activate"
cd /d "%~dp0"
if /i "%TESTS%"=="igt" (
    set TEST_PATH=fus_driving_systems/tests/hardware/test_igt_hardware.py
) else if /i "%TESTS%"=="sc" (
    set TEST_PATH=fus_driving_systems/tests/hardware/test_sonic_concepts_hardware.py
) else (
    echo Set TESTS to igt or sc at the top of this file.
    goto :end
)
python -m pytest -m hardware --no-cov %TEST_PATH% %*

:: Keep the window open when started by double-clicking.
:end
echo %cmdcmdline% | findstr /i /c:"/c" >nul && pause
endlocal
