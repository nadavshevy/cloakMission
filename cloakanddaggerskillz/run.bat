@echo off

set dir=%~dp0

rem this script will always take you first of all to current directory
cd /d "%dir%"

set pyexe=C:\python27\python.exe
rem check if python installed
if not exist %pyexe% (
    rem now we try with regular python
    where python > nul 2> nul
    if ERRORLEVEL 1 goto :nopython
    set pyexe=python
)

rem call run.py with the arguments given (except the first argument, which is the bat's name)
"%pyexe%" "%dir%run.py" --load-time 10000 -I -e -E -d -O --debug-in-replay --log-dir "%dir%lib\game_logs" %*

rem see ya
goto:EOF


:nopython
@echo ERROR: Python is not installed OR Python not in PATH. Check if you have Python 2.7 installed.
exit /B 1