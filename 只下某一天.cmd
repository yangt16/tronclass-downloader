@echo off
REM ===========================================================
REM  Download only ONE DAY (or several days) of lectures.
REM
REM  Asks for a date, then runs the normal batch with a filter.
REM  Works on every list in lists\ at once: days that a course
REM  does not have are simply ignored.
REM
REM  Examples of what you can type:
REM     20261030              one day
REM     20261030,20261104     several days
REM     (empty)               no filter, download everything
REM
REM  The list is NOT archived when filtering, so it stays usable.
REM
REM  HARD RULES: ASCII only, no angle brackets in comments, CRLF.
REM ===========================================================
setlocal
chcp 65001 >nul

echo ============================================================
echo  Download only selected day(s)
echo ============================================================
set "DAY="
set /p "DAY=Date(s) to download - YYYYMMDD, comma for several, empty=all: "

if not defined DAY goto runall

REM validate: digits and commas only
echo %DAY%| findstr /r "^[0-9][0-9,]*$" >nul
if errorlevel 1 goto bad

set "GETLEC_ONLY=%DAY%"
goto run

:bad
echo.
echo [day] ERROR: bad input: "%DAY%"
echo       Use 8 digits, e.g. 20261030 or 20261030,20261104
echo.
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 1

:runall
echo.
echo [day] no filter, downloading everything

:run
echo.
call "%~dp0getlec.cmd" %*
exit /b %ERRORLEVEL%
