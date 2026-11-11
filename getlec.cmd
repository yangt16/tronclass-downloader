@echo off
REM ===========================================================
REM  getlec.cmd - download lectures listed in lists\*.txt
REM
REM  The only entry point. Create lists\MyCourse.txt yourself,
REM  paste playback URLs into it (one per line), run this file.
REM  The list name becomes the course name and the folder name:
REM      lists\MYCOURSE.txt   gives   media\MYCOURSE\
REM
REM  usage:
REM     getlec.cmd                    download everything in lists\
REM     getlec.cmd --all              same as above
REM     getlec.cmd lists\MYCOURSE.txt only that one list
REM     getlec.cmd lists\X.txt INSTRUCTOR   pick another track
REM
REM  HARD RULES FOR THIS FILE:
REM    1. ASCII ONLY. Not even Chinese in comments -- cmd.exe
REM       decodes .cmd as GBK and UTF-8 CJK bytes break parsing.
REM    2. NO angle brackets in comments. cmd parses redirection
REM       characters even on REM lines, which shreds the comment
REM       into junk commands. Both mistakes have caused real
REM       floods and loops before.
REM ===========================================================
setlocal
chcp 65001 >nul
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "FIRST=%~1"
set "TRACK=%~2"

REM ---------- find python (each candidate must actually run) ----------
set "PYEXE="
if exist "%ROOT%\python\python.exe" call :trypy "%ROOT%\python\python.exe"
if defined PYEXE goto havepy
for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYEXE call :trypy "%%P"
if defined PYEXE goto havepy
for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined PYEXE call :trypy "%%P"
if defined PYEXE goto havepy
echo.
echo [getlec] ERROR: Python not found.
echo         Install Python 3.8+ from python.org, or drop a portable
echo         python into %ROOT%\python\
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 9009
:havepy

set "PY=%PYEXE%"
set "DRYARG="
if "%GETLEC_DRYRUN%"=="1" set "DRYARG=--dry-run"
set "DROPARG="
if "%GETLEC_DROPVIDEO%"=="1" set "DROPARG=--drop-video"

if not "%TRACK%"=="" goto hafetrack
set "TRACK=ENCODER"
:hafetrack

if not exist "%ROOT%\tools\lectures.py" goto notools

if "%FIRST%"=="" goto batch
if /i "%FIRST%"=="--all" goto batch
call :run_one "%FIRST%"
goto done

REM ===========================================================
REM  batch: every lists\*.txt that has at least one address
REM ===========================================================
:batch
echo [getlec] BATCH mode over %ROOT%\lists
echo.
set "CNT=0"
"%PY%" "%ROOT%\tools\lists.py"
if errorlevel 1 goto done
for /f "delims=" %%L in ('dir /b /o-n "%ROOT%\lists\*.txt" 2^>nul') do call :run_one "%ROOT%\lists\%%L"
if "%CNT%"=="0" echo [getlec] nothing to do
goto done

REM -----------------------------------------------------------
REM  :run_one  %1 = list path
REM -----------------------------------------------------------
:run_one
set "LIST=%~1"
if not exist "%LIST%" set "LIST=%ROOT%\%~1"
if not exist "%LIST%" goto p_missing
set /a CNT+=1
echo ============================================================
echo [getlec] LIST %LIST%
echo [getlec] track=%TRACK%
echo ============================================================
"%PY%" "%ROOT%\tools\lectures.py" --urls "%LIST%" --track "%TRACK%" %DRYARG% %DROPARG%
if errorlevel 1 goto p_failed
echo [getlec] OK
echo.
exit /b 0

:p_missing
echo [getlec] SKIP missing: %~1
exit /b 1

:p_failed
echo [getlec] FAILED: %LIST%   kept in place, not archived
echo.
exit /b 1

:notools
echo [getlec] ERROR: %ROOT%\tools\lectures.py not found
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 1

:done
echo.
"%PY%" "%ROOT%\tools\make_index.py"
if "%GETLEC_NOPAUSE%"=="" pause
exit /b 0

REM -----------------------------------------------------------
REM  subroutines at the very end: the main flow must not fall
REM  through into them (that was a real bug once).
REM -----------------------------------------------------------
:trypy
"%~1" -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYEXE=%~1"
exit /b 0
